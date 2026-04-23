import sounddevice as sd
from faster_whisper import WhisperModel
import requests
import subprocess
import uuid
import os
import numpy as np

# ---------------- CONFIG ----------------
SAMPLE_RATE = 16000
RECORD_SECONDS = 7

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3"

PIPER_PATH = "./piper/piper"

VOICE_MODELS = {
    "en": "./voices/en_US-lessac-medium.onnx",
    "hi": "./voices/hi_IN-rohan-medium.onnx"
}

DEFAULT_LANG = "en"

# ---------------- LOAD WHISPER ----------------
print("Loading Whisper model...")
whisper = WhisperModel("base", compute_type="int8")
print("✅ Whisper Loaded")

# ---------------- RECORD ----------------
def record_audio():
    print("🎤 Listening...")

    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='float32'
    )

    sd.wait()

    # Normalize audio
    audio = audio.flatten()
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val

    return audio

# ---------------- TRANSCRIBE ----------------
def transcribe(audio):
    # First pass (auto detect)
    segments, info = whisper.transcribe(
        audio,
        beam_size=5,
        vad_filter=True
    )

    text = " ".join([s.text for s in segments]).strip()
    lang = info.language if info.language else DEFAULT_LANG

    # 🔥 If Hindi → re-run with Hindi prompt
    if lang == "hi":
        segments, _ = whisper.transcribe(
            audio,
            language="hi",
            initial_prompt="यह हिंदी भाषा है। देवनागरी लिपि में लिखें।"
        )
        text = " ".join([s.text for s in segments]).strip()

    print(f"🔍 Detected Language: {lang}")
    print(f"📝 You: {text}")

    return text, lang
# ---------------- AI ----------------
messages = [
    {"role": "system", "content": "You are a helpful voice assistant. Keep answers short."}
]

def ask_ai(text, lang):
    # 🔥 Force correct script + language
    prompt = f"""
User said: {text}

If the text is Hindi but not in Devanagari, convert it to proper Hindi.

Reply ONLY in {lang}.
Keep response short.
"""

    messages.append({"role": "user", "content": prompt})

    r = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "messages": messages,
        "stream": False
    })

    reply = r.json()["message"]["content"]
    messages.append({"role": "assistant", "content": reply})

    return reply

# ---------------- TTS ----------------
def speak(text, lang):
    print(f"🤖 AI ({lang}): {text}")

    file = f"/tmp/{uuid.uuid4()}.wav"

    voice_model = VOICE_MODELS.get(lang, VOICE_MODELS[DEFAULT_LANG])

    # fallback if Hindi voice missing
    if not os.path.exists(voice_model):
        print("⚠️ Voice not found, using English")
        voice_model = VOICE_MODELS["en"]

    subprocess.run([
        PIPER_PATH,
        "--model",
        voice_model,
        "--output_file",
        file
    ], input=text.encode("utf-8"), check=True)

    subprocess.run(["aplay", file], check=True)

# ---------------- MAIN LOOP ----------------
print("\n🎙️ Multilingual Voice AI Ready (Hindi + English)\n")

while True:
    try:
        audio = record_audio()

        text, lang = transcribe(audio)

        if not text:
            continue

        reply = ask_ai(text, lang)

        speak(reply, lang)

    except KeyboardInterrupt:
        print("\nStopping...")
        break