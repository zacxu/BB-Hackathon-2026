# OmniBridge

**OmniBridge** is a web app for adaptive communication: **User A** can input via **hand gestures (ASL)** or text; **User B** can input via **speech** or text. No chat/WebSocket—each side has a message box fed by gesture, speech, or typing.

---

## File structure

```
Omnibridge/
├── README.md                 # This file: project overview, setup, usage
├── SPEECH_SETUP.md           # Speech stack (SpeechRecognition, pyttsx3, PyAudio)
├── requirements.txt          # Python dependencies
├── .gitignore
│
├── backend/                  # FastAPI server
│   ├── __init__.py
│   └── main.py               # Routes, ASL model API, speech TTS/STT API
│
├── frontend/                 # Static web UI
│   ├── index.html            # Page structure (User A & User B cards)
│   ├── style.css             # Layout and styling
│   └── app.js                # Gesture (MediaPipe + ASL API), speech (record → STT), TTS
│
├── CVhandsv2/                # ASL hand-sign model and scripts
│   ├── model.p               # Trained classifier (pickle), used by backend + inference_classifier
│   ├── inference_classifier.py  # Standalone script: camera → MediaPipe → model → letters
│   ├── create_dataset.py     # Dataset building (42 features from 21 landmarks)
│   ├── train_classifier.py   # Train model.p from dataset
│   ├── collect_imgs.py       # Image collection for dataset
│   ├── mediapipe_compat.py   # MediaPipe helpers
│   ├── data.pickle           # Dataset artifact
│   └── hand_landmarker.task  # MediaPipe hand model asset
│
└── terminal_speech_assistant.py   # Standalone CLI: SpeechRecognition + pyttsx3 (reference for speech API)
```

---

## Project overview

- **User A (Gesture / Text)**  
  - **Camera** – Opens browser webcam; hand landmarks are drawn with MediaPipe Hands.  
  - **Start gesture** – Starts “recording” gestures. Hand pose is sent to the backend; the same 42-feature ASL model as in `CVhandsv2/inference_classifier.py` predicts a letter (A–Y, no J). After the same letter is held for **2 seconds**, it is appended to the message box once. **Stop** ends recording and turns off the camera; a space is added to the message.  
  - **Message** – Shows the spelled-out gesture text; can also be typed.

- **User B (Speech / Text)**  
  - **Start speaking** – Records from the microphone (MediaRecorder → WAV in browser).  
  - **Stop** – Sends the WAV to the backend; **SpeechRecognition** with Google’s free web API transcribes it and the result is shown in the message box.  
  - **Speak** – Sends the current message text to the backend; **pyttsx3** returns WAV and the browser plays it (TTS).  
  - **Upload audio** – Upload a WAV file; backend transcribes it and appends to the message.  
  - **Message** – Shows transcribed speech or typed text.

The backend does **not** run the Python camera script; it only loads `model.p` and exposes APIs. The browser handles camera and recording.

---

## Setup

### 1. Python environment

- Python 3.8+ recommended.
- Create and use a virtual environment (optional but recommended):

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Run the server

From the project root:

```
uvicorn backend.main:app --reload
```

- App: **http://127.0.0.1:8000**


---

## Usage

1. Open **http://127.0.0.1:8000** in a browser (Chrome or Edge recommended for media).
2. **User A**  
   - Click **Camera** to start the webcam and see hand landmarks.  
   - Click **Start gesture** to begin spelling; hold each letter for 2 seconds to add it. Click **Stop** to finish (adds a space and turns off the camera).
3. **User B**  
   - Click **Start speaking**, speak for at least ~2 seconds, then **Stop**. The transcribed text appears in the message box.  
   - Use **Speak** to hear the current message (TTS).  
   - Use **Upload audio** to transcribe a WAV file.

If speech is not detected, a short tip appears under the User B message box (“speak clearly for 2+ seconds, check mic is selected”).

---

## Design and implementation notes

### ASL gesture pipeline

- **Frontend**: MediaPipe Hands on the browser video stream; 21 hand landmarks per frame. While “Start gesture” is active, landmarks are sent to `POST /api/gesture/asl`.
- **Backend**: Builds the same **42 features** as in `CVhandsv2/create_dataset.py` and `inference_classifier.py`: for each of 21 landmarks, `x - min(all_x)` and `y - min(all_y)`. 
- **Confirmation**: The same letter must be held for 2 seconds to be appended once; `lastConfirmedLetter` prevents duplicate letters from repeated API callbacks.

### Speech pipeline

- **STT**: Browser records with MediaRecorder → WAV (or WebM decoded to WAV in Chrome/Edge). Frontend sends the file to `POST /api/speech/stt`. Backend uses **SpeechRecognition** (`recognize_google`) and optional volume normalization; returns `{"text": "...", "understood": true/false}`. No Google Cloud API key; uses the same free web API as **terminal_speech_assistant.py**.
- **TTS**: Frontend sends message text to `POST /api/speech/tts`. Backend uses **pyttsx3** to generate WAV and returns the audio; the browser plays it.

### Relevant resources

- **CVhandsv2/inference_classifier.py** – Reference for feature extraction, model usage, and 2-second confirmation logic (standalone camera script; the web app does not run it).
- **CVhandsv2/create_dataset.py** – Defines the 42-feature scheme (21 landmarks → relative x,y).
- **terminal_speech_assistant.py** – Reference for SpeechRecognition and pyttsx3 usage (CLI); the backend exposes the same ideas as HTTP APIs.
- **SPEECH_SETUP.md** – Speech stack install and behavior (SpeechRecognition, pyttsx3, PyAudio).

---

## API summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Serves `frontend/index.html` |
| GET | `/static/*` | Serves frontend assets (JS, CSS) |
| POST | `/api/gesture/asl` | Body: `{ "landmarks": [[x,y,z], ...] }` (21 points). Returns `{ "letter": "A" \| null }`. |
| POST | `/api/speech/tts` | Body: `{ "text": "..." }`. Returns WAV audio. |
| POST | `/api/speech/stt` | Form: `file` (WAV or WebM). Returns `{ "text": "...", "understood": true \| false }`. |

---

## License and credits

- MediaPipe Hands: [Google MediaPipe](https://developers.google.com/mediapipe)
- SpeechRecognition: [SpeechRecognition](https://github.com/Uberi/speech_recognition) (Google web API used for STT)
- pyttsx3: [pyttsx3](https://github.com/nateshmbhat/pyttsx3) for TTS
