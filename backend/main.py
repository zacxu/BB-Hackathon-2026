from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
import os
import pickle
import subprocess
import tempfile
import numpy as np

# Speech: SpeechRecognition (recognize_google) + pyttsx3 (same as terminal_speech_assistant.py)
try:
    import speech_recognition as sr
except ImportError:
    sr = None
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

app = FastAPI()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_PATH = os.path.join(PROJECT_ROOT, "CVhandsv2", "model.p")

# Same labels as inference_classifier.py (0-23 -> A-Y, no J)
_LABELS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y"]
_model = None

def _get_model():
    global _model
    if _model is None:
        with open(MODEL_PATH, "rb") as f:
            _model = pickle.load(f)["model"]
    return _model

def _predict_letter(landmarks):
    """Same feature extraction as inference_classifier.py / create_dataset.py: 21 landmarks -> 42 features (x-min(x_), y-min(y_))."""
    if not landmarks or len(landmarks) < 21:
        return None
    x_ = [p[0] for p in landmarks[:21]]
    y_ = [p[1] for p in landmarks[:21]]
    features = []
    for i in range(21):
        features.append(landmarks[i][0] - min(x_))
        features.append(landmarks[i][1] - min(y_))
    if len(features) != 42:
        return None
    model = _get_model()
    pred = model.predict([np.asarray(features)])[0]
    try:
        idx = int(pred)
    except (TypeError, ValueError):
        return None
    if 0 <= idx < 24:
        return _LABELS[idx]
    return None

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def root():
    return FileResponse("frontend/index.html")

class GestureRequest(BaseModel):
    landmarks: list  # 21 points [x, y] or [x, y, z]

@app.post("/api/gesture/asl")
def gesture_asl(req: GestureRequest):
    letter = _predict_letter(req.landmarks)
    return {"letter": letter}


# ---------- Speech Assistant API (terminal_speech_assistant.py) ----------

_tts_engine = None

def _get_tts():
    global _tts_engine
    if pyttsx3 is None:
        raise HTTPException(status_code=503, detail="pyttsx3 not installed")
    if _tts_engine is None:
        try:
            _tts_engine = pyttsx3.init()
            _tts_engine.setProperty("rate", 180)
            _tts_engine.setProperty("volume", 0.9)
            voices = _tts_engine.getProperty("voices")
            if voices:
                _tts_engine.setProperty("voice", voices[0].id)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"TTS init failed: {e}")
    return _tts_engine


class TTSRequest(BaseModel):
    text: str


@app.post("/api/speech/tts")
def speech_tts(req: TTSRequest):
    """Text-to-speech: same logic as terminal_speech_assistant.text_to_speech(). Returns WAV audio."""
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    try:
        engine = _get_tts()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            engine.save_to_file(text, path)
            engine.runAndWait()
            with open(path, "rb") as f:
                data = f.read()
            return Response(content=data, media_type="audio/wav")
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _normalize_wav_volume(wav_bytes: bytes, headroom: float = 0.8) -> bytes:
    """Boost quiet WAV so peak is at headroom of full scale. Returns new WAV bytes."""
    if len(wav_bytes) < 44 or wav_bytes[:4] != b"RIFF" or wav_bytes[8:12] != b"WAVE":
        return wav_bytes
    import struct
    pcm = wav_bytes[44:]
    if len(pcm) % 2:
        return wav_bytes
    samples = list(struct.unpack(f"<{len(pcm)//2}h", pcm))
    if not samples:
        return wav_bytes
    peak = max(abs(s) for s in samples)
    if peak < 100:
        return wav_bytes
    target = int(32767 * headroom)
    if peak >= target:
        return wav_bytes
    gain = target / peak
    new_samples = [max(-32768, min(32767, int(s * gain))) for s in samples]
    new_pcm = struct.pack(f"<{len(new_samples)}h", *new_samples)
    return wav_bytes[:44] + new_pcm


def _webm_to_wav(contents: bytes) -> bytes:
    """Convert webm audio to WAV using ffmpeg. Returns WAV bytes."""
    fd_in, path_in = tempfile.mkstemp(suffix=".webm")
    fd_out, path_out = tempfile.mkstemp(suffix=".wav")
    try:
        os.close(fd_out)
        with os.fdopen(fd_in, "wb") as f:
            f.write(contents)
        subprocess.run(
            ["ffmpeg", "-y", "-i", path_in, "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", path_out],
            check=True,
            capture_output=True,
        )
        with open(path_out, "rb") as f:
            return f.read()
    finally:
        for p in (path_in, path_out):
            try:
                os.unlink(p)
            except Exception:
                pass


@app.post("/api/speech/stt")
async def speech_stt(file: UploadFile = File(...)):
    """Speech-to-text using SpeechRecognition + recognize_google (same as terminal_speech_assistant.py). WAV or WebM."""
    if sr is None:
        raise HTTPException(status_code=503, detail="SpeechRecognition not installed (pip install SpeechRecognition)")
    recognizer = sr.Recognizer()
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty file")
        is_webm = contents[:4] == b"\x1aE\xdf\xa3" or (file.filename or "").lower().endswith(".webm")
        if is_webm:
            try:
                contents = _webm_to_wav(contents)
            except FileNotFoundError:
                raise HTTPException(status_code=503, detail="ffmpeg not installed; browser sends WAV by default")
            except subprocess.CalledProcessError as e:
                err = (e.stderr or b"").decode(errors="replace") if getattr(e, "stderr", None) else str(e)
                raise HTTPException(status_code=400, detail=f"ffmpeg failed: {err}")
        if contents[:4] != b"RIFF":
            raise HTTPException(status_code=400, detail="Upload WAV or WebM audio")
        contents = _normalize_wav_volume(contents)
        path = tempfile.mktemp(suffix=".wav")
        try:
            with open(path, "wb") as f:
                f.write(contents)
            with sr.AudioFile(path) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="en-US")
            return {"text": text, "understood": True}
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass
    except sr.UnknownValueError:
        return {"text": "", "understood": False}
    except sr.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Speech API error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
