/* ---------------- ELEMENTS ---------------- */

const aText = document.getElementById("aText");
const bText = document.getElementById("bText");
const gestureToggleBtn = document.getElementById("gestureToggle");
const trainLettersBtn = document.getElementById("trainLettersBtn");
const trainLettersModal = document.getElementById("trainLettersModal");
const trainLetterInput = document.getElementById("trainLetterInput");
const trainLettersClose = document.getElementById("trainLettersClose");
const startSpeechBtn = document.getElementById("startSpeech");
const stopSpeechBtn = document.getElementById("stopSpeech");
const speakTtsBtn = document.getElementById("speakTts");
const sttFileInput = document.getElementById("sttFileInput");

/* ---------------- BROWSER WEBCAM + CVhandsv2 MODEL (no Python script) ---------------- */

const videoEl = document.getElementById("cam");
const canvasEl = document.getElementById("overlay");
const ctx = canvasEl.getContext("2d");
const mediaEl = document.querySelector(".card .media");
const cameraChipEl = document.getElementById("cameraChip");

let camera = null;
let hands = null;
let browserCameraOn = false;
let gestureRecording = false;
let recordedString = "";
let lastDetectedLetter = null;
let detectionStartTime = null;
/** Last letter we added (so we only add once per hold, not every 2s or every callback). */
let lastConfirmedLetter = null;
const CONFIRMATION_TIME = 2;

async function classifyASL(landmarks) {
  const res = await fetch("/api/gesture/asl", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ landmarks }),
  });
  const data = await res.json();
  return data.letter || null;
}

function drawLetterBox(w, h) {
  const pad = 16;
  const boxW = 200;
  const boxH = 100;
  const x = pad;
  const y = pad;
  const now = Date.now() / 1000;
  const letter = lastDetectedLetter != null ? lastDetectedLetter : "—";
  const elapsed = detectionStartTime != null ? now - detectionStartTime : 0;
  const progress = lastDetectedLetter != null ? Math.min(1, elapsed / CONFIRMATION_TIME) : 0;
  const barH = 8;
  const barW = boxW - 24;
  const barY = y + boxH - pad - barH;

  ctx.save();
  ctx.strokeStyle = "rgba(255,255,255,0.9)";
  ctx.lineWidth = 2;
  ctx.fillStyle = "rgba(0,0,0,0.6)";
  ctx.beginPath();
  ctx.roundRect(x, y, boxW, boxH, 10);
  ctx.fill();
  ctx.stroke();

  ctx.font = "bold 36px sans-serif";
  ctx.fillStyle = "rgba(255,255,255,0.95)";
  ctx.textAlign = "center";
  ctx.fillText(letter, x + boxW / 2, y + 38);
  ctx.font = "11px sans-serif";
  ctx.fillStyle = "rgba(255,255,255,0.7)";
  ctx.fillText("Hold 2s to add", x + boxW / 2, y + 54);

  ctx.fillStyle = "rgba(255,255,255,0.3)";
  ctx.fillRect(x + 12, barY, barW, barH);
  ctx.fillStyle = progress >= 1 ? "rgba(34,197,94,0.95)" : "rgba(59,130,246,0.95)";
  ctx.fillRect(x + 12, barY, barW * progress, barH);
  ctx.strokeStyle = "rgba(255,255,255,0.5)";
  ctx.lineWidth = 1;
  ctx.strokeRect(x + 12, barY, barW, barH);

  if (recordedString.length > 0) {
    ctx.font = "12px sans-serif";
    ctx.fillStyle = "rgba(255,255,255,0.8)";
    ctx.textAlign = "left";
    ctx.fillText("So far: " + recordedString, x + 12, y + boxH + 18);
  }
  ctx.restore();
}

function onCameraFrame(results) {
  const w = videoEl.videoWidth || 640;
  const h = videoEl.videoHeight || 480;
  canvasEl.width = w;
  canvasEl.height = h;
  ctx.clearRect(0, 0, w, h);

  const handsList = results.multiHandLandmarks;
  if (handsList && handsList.length > 0) {
    const lm = handsList[0];
    ctx.fillStyle = "rgba(255,255,255,0.6)";
    lm.forEach((p) => {
      ctx.beginPath();
      ctx.arc(p.x * w, p.y * h, 3, 0, Math.PI * 2);
      ctx.fill();
    });

    if (gestureRecording) {
      const landmarks = lm.map((p) => [p.x, p.y, p.z]);
      classifyASL(landmarks).then((letter) => {
        if (letter == null) return;
        const now = Date.now() / 1000;
        if (letter !== lastDetectedLetter) {
          lastDetectedLetter = letter;
          detectionStartTime = now;
          lastConfirmedLetter = null;
        } else if (detectionStartTime != null) {
          const elapsed = now - detectionStartTime;
          if (elapsed >= CONFIRMATION_TIME && letter !== lastConfirmedLetter) {
            recordedString += letter;
            aText.value = recordedString;
            lastConfirmedLetter = letter;
          }
        }
      });
    }
  } else {
    lastDetectedLetter = null;
    detectionStartTime = null;
    lastConfirmedLetter = null;
  }

  if (gestureRecording) drawLetterBox(w, h);
}

async function startBrowserCamera() {
  if (browserCameraOn) return;
  if (!hands) {
    hands = new Hands({
      locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`,
    });
    hands.setOptions({
      maxNumHands: 1,
      modelComplexity: 0,
      minDetectionConfidence: 0.3,
      minTrackingConfidence: 0.3,
    });
    hands.onResults(onCameraFrame);
    camera = new Camera(videoEl, {
      onFrame: async () => await hands.send({ image: videoEl }),
      width: 640,
      height: 480,
    });
  }
  if (!camera) return;
  browserCameraOn = true;
  videoEl.muted = true;
  camera.start();
}

function stopBrowserCamera() {
  if (!browserCameraOn) return;
  browserCameraOn = false;
  if (camera && typeof camera.stop === "function") camera.stop();
}

function updateGestureButtonLabel() {
  if (gestureToggleBtn) gestureToggleBtn.textContent = gestureRecording ? "Stop" : "Start gesture";
}

function startGesture() {
  if (gestureRecording) return;
  if (!browserCameraOn) {
    startBrowserCamera();
  }
  gestureRecording = true;
  recordedString = aText.value.trim();
  aText.value = recordedString;
  lastDetectedLetter = null;
  detectionStartTime = null;
  lastConfirmedLetter = null;
  updateGestureButtonLabel();
}

function stopGesture() {
  if (!gestureRecording) return;
  gestureRecording = false;
  const box = document.getElementById("aText");
  if (box) {
    const current = (box.value || "").trimEnd();
    box.value = current + " ";
    box.dispatchEvent(new Event("input", { bubbles: true }));
  }
  recordedString = box ? box.value : "";
  updateGestureButtonLabel();
  // Defer stopping camera so the textarea update is committed first
  setTimeout(stopBrowserCamera, 0);
}

if (gestureToggleBtn) {
  gestureToggleBtn.onclick = () => (gestureRecording ? stopGesture() : startGesture());
}

function openTrainLettersModal() {
  if (!browserCameraOn) startBrowserCamera();
  if (trainLetterInput) {
    trainLetterInput.value = "";
    trainLetterInput.placeholder = "e.g. A";
  }
  if (trainLettersModal) trainLettersModal.hidden = false;
}
function closeTrainLettersModal() {
  if (trainLettersModal) trainLettersModal.hidden = true;
}

if (trainLettersBtn) trainLettersBtn.onclick = openTrainLettersModal;
if (trainLettersClose) trainLettersClose.onclick = closeTrainLettersModal;
if (trainLettersModal) {
  const backdrop = trainLettersModal.querySelector(".trainModalBackdrop");
  if (backdrop) backdrop.onclick = closeTrainLettersModal;
}
if (trainLetterInput) {
  trainLetterInput.oninput = () => {
    const v = trainLetterInput.value.toUpperCase().replace(/[^A-Z]/g, "");
    if (v.length > 1) trainLetterInput.value = v.slice(0, 1);
    else if (v && v !== trainLetterInput.value) trainLetterInput.value = v;
  };
}

if (cameraChipEl) {
  cameraChipEl.style.cursor = "pointer";
  cameraChipEl.addEventListener("click", startBrowserCamera);
}

/* ---------------- SPEECH TO TEXT (User B) ---------------- */

/* Record with MediaRecorder, decode to WAV in browser (16 kHz mono), send to /api/speech/stt. */
const SPEECH_SAMPLE_RATE = 16000;
let speechStream = null;
let speechRecorder = null;
let speechChunks = [];
let speechRecording = false;

function makeWavBlob(pcmInt16, sampleRate) {
  const numChannels = 1;
  const bytesPerSample = 2;
  const dataLength = pcmInt16.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataLength);
  const view = new DataView(buffer);
  const writeStr = (offset, str) => { for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i)); };
  writeStr(0, "RIFF");
  view.setUint32(4, 36 + dataLength, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * numChannels * bytesPerSample, true);
  view.setUint16(32, numChannels * bytesPerSample, true);
  view.setUint16(34, 16, true);
  writeStr(36, "data");
  view.setUint32(40, dataLength, true);
  for (let i = 0; i < pcmInt16.length; i++) view.setInt16(44 + i * 2, pcmInt16[i], true);
  return new Blob([buffer], { type: "audio/wav" });
}

function floatTo16BitPCM(float32Array) {
  const pcm = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  return pcm;
}

function resampleTo16k(pcmInt16, fromRate) {
  if (fromRate === SPEECH_SAMPLE_RATE) return pcmInt16;
  const outLength = Math.floor(pcmInt16.length * SPEECH_SAMPLE_RATE / fromRate);
  const out = new Int16Array(outLength);
  for (let i = 0; i < outLength; i++) {
    const srcIdx = (i * fromRate) / SPEECH_SAMPLE_RATE;
    const j = Math.floor(srcIdx);
    const frac = srcIdx - j;
    const a = pcmInt16[Math.min(j, pcmInt16.length - 1)];
    const b = pcmInt16[Math.min(j + 1, pcmInt16.length - 1)];
    out[i] = Math.round(a + frac * (b - a));
  }
  return out;
}

async function webmBlobToWavBlob(webmBlob) {
  const arrayBuffer = await webmBlob.arrayBuffer();
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const audioBuffer = await ctx.decodeAudioData(arrayBuffer.slice(0));
  const ch0 = audioBuffer.getChannelData(0);
  let pcm = floatTo16BitPCM(ch0);
  let max = 0;
  for (let i = 0; i < pcm.length; i++) {
    const a = Math.abs(pcm[i]);
    if (a > max) max = a;
  }
  if (max > 0 && max < 8000) {
    const gain = 16000 / max;
    for (let i = 0; i < pcm.length; i++) {
      const v = Math.round(pcm[i] * gain);
      pcm[i] = Math.max(-32768, Math.min(32767, v));
    }
  }
  const pcm16k = resampleTo16k(pcm, audioBuffer.sampleRate);
  return makeWavBlob(pcm16k, SPEECH_SAMPLE_RATE);
}

async function startSpeechRecording() {
  if (speechRecording) return;
  const tipEl = document.getElementById("speechTip");
  if (tipEl) { tipEl.removeAttribute("data-visible"); tipEl.hidden = true; }
  try {
    speechStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm";
    speechRecorder = new MediaRecorder(speechStream, { mimeType: mime });
    speechChunks = [];
    speechRecorder.ondataavailable = (e) => { if (e.data.size > 0) speechChunks.push(e.data); };
    speechRecorder.start(200);
    speechRecording = true;
    console.log("[Speech] Recording (MediaRecorder), will convert to WAV on Stop");
  } catch (e) {
    console.error("[Speech] Mic error:", e);
    alert("Microphone access needed. Please allow mic and try again.");
  }
}

async function stopSpeechRecording() {
  if (!speechRecording || !speechRecorder) return;
  speechRecording = false;
  const recorder = speechRecorder;
  const stream = speechStream;
  speechRecorder = null;
  speechStream = null;
  stream.getTracks().forEach((t) => t.stop());

  const box = document.getElementById("bText");
  const startContent = (box && box.value || "").trimEnd();

  await new Promise((r) => { recorder.onstop = r; recorder.stop(); });
  const webmBlob = new Blob(speechChunks, { type: "audio/webm" });
  speechChunks = [];

  if (webmBlob.size < 2000) {
    console.log("[Speech] Recording too short");
    if (box) box.value = startContent;
    return;
  }

  let wavBlob;
  try {
    wavBlob = await webmBlobToWavBlob(webmBlob);
  } catch (decodeErr) {
    console.error("[Speech] WebM decode failed:", decodeErr);
    alert("Could not process recording. Please use Chrome or Edge and try again.");
    if (box) box.value = startContent;
    return;
  }

  if (!wavBlob || wavBlob.size < 1000) {
    if (box) box.value = startContent;
    return;
  }

  try {
    const form = new FormData();
    form.append("file", wavBlob, "recording.wav");
    const res = await fetch("/api/speech/stt", { method: "POST", body: form });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || res.statusText);
    const text = (data.text || "").trim();
    const understood = data.understood !== false;
    console.log("[Speech] Backend returned:", JSON.stringify(text), understood ? "" : "(no speech detected)");
    if (box) {
      box.value = text ? (startContent ? startContent + " " + text : text) : startContent;
      box.dispatchEvent(new Event("input", { bubbles: true }));
    }
    const tipEl = document.getElementById("speechTip");
    if (!understood && !text) {
      if (tipEl) {
        tipEl.removeAttribute("hidden");
        tipEl.setAttribute("data-visible", "true");
        setTimeout(() => { tipEl.removeAttribute("data-visible"); tipEl.hidden = true; }, 6000);
      }
    } else if (tipEl) {
      tipEl.removeAttribute("data-visible");
      tipEl.hidden = true;
    }
  } catch (e) {
    console.error("[Speech] STT error:", e);
    alert("Transcription failed: " + (e.message || e));
    if (box) box.value = startContent;
  }
}

if (startSpeechBtn) startSpeechBtn.onclick = () => startSpeechRecording();
if (stopSpeechBtn) stopSpeechBtn.onclick = () => stopSpeechRecording();

/* Backend speech API (terminal_speech_assistant.py) */
async function speakTts() {
  const text = (bText && bText.value || "").trim();
  if (!text) return;
  if (speakTtsBtn) speakTtsBtn.disabled = true;
  try {
    const res = await fetch("/api/speech/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => URL.revokeObjectURL(url);
    await audio.play();
  } catch (e) {
    console.error("TTS error:", e);
    alert("Text-to-speech failed: " + (e.message || e));
  } finally {
    if (speakTtsBtn) speakTtsBtn.disabled = false;
  }
}

async function handleSttFile(file) {
  if (!file || !bText) return;
  const btn = document.querySelector('[for="sttFileInput"]');
  if (btn) btn.disabled = true;
  try {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/api/speech/stt", { method: "POST", body: form });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    const prev = (bText.value || "").trimEnd();
    bText.value = prev ? prev + " " + data.text : data.text;
  } catch (e) {
    console.error("STT error:", e);
    alert("Speech-to-text failed: " + (e.message || e));
  } finally {
    if (btn) btn.disabled = false;
    sttFileInput.value = "";
  }
}

if (speakTtsBtn) speakTtsBtn.onclick = speakTts;
if (sttFileInput) sttFileInput.onchange = () => { if (sttFileInput.files[0]) handleSttFile(sttFileInput.files[0]); };
