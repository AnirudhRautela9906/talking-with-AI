import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import requests
import subprocess
import queue
import time

# ---------------- CONFIG ----------------
SAMPLE_RATE = 16000
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "tinyllama"

PIPER_PATH = "./piper/piper"
VOICE_MODEL = "./voices/en_US-lessac-medium.onnx"

SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 2  # seconds

# ---------------- INIT ----------------
print("Loading Whisper model...")
whisper = WhisperModel("base", compute_type="int8")

audio_queue = queue.Queue()

# ---------------- AUDIO STREAM ----------------
def audio_callback(indata, frames, time_info, status):
    audio_queue.put(indata.copy())

def record_until_silence():
    print("🎤 Listening...")

    recorded_audio = []
    silence_start = None

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        callback=audio_callback
    ):
        while True:
            chunk = audio_queue.get()
            recorded_audio.append(chunk)

            volume = np.sqrt(np.mean(chunk**2))

            if volume < SILENCE_THRESHOLD:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > SILENCE_DURATION:
                    print("⏹️ Silence detected")
                    break
            else:
                silence_start = None

    return np.concatenate(recorded_audio).flatten()

# ---------------- TRANSCRIBE ----------------
def transcribe(audio):
    segments, _ = whisper.transcribe(audio)
    return " ".join([s.text for s in segments]).strip()

# ---------------- AI ----------------
messages = [
    {"role": "system", "content": "You are Jarvis, a helpful voice assistant. Keep answers short."}
]

def ask_ai(text):
    messages.append({"role": "user", "content": text})

    r = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "messages": messages,
        "stream": False
    })

    reply = r.json()["message"]["content"]
    messages.append({"role": "assistant", "content": reply})
    return reply

# ---------------- TTS ----------------
def speak(text):
    print("Jarvis:", text)

    output_file = "/tmp/jarvis_output.wav"

    subprocess.run([
        PIPER_PATH,
        "--model",
        VOICE_MODEL,
        "--output_file",
        output_file
    ], input=text.encode("utf-8"), check=True)

    subprocess.run(["aplay", output_file], check=True)

# ---------------- START ----------------
print("\n🤖 Starting Jarvis...\n")

# Initial introduction
intro_text = "Hello, I am Jarvis, your personal voice assistant. How can I help you?"
speak(intro_text)

# ---------------- MAIN LOOP ----------------
while True:
    try:
        audio = record_until_silence()
        text = transcribe(audio)

        if not text:
            continue

        print("You:", text)

        # Exit condition
        if "thank you jarvis" in text.lower():
            speak("Bye bye! See you soon....")
            print("👋 Exiting...")
            break

        reply = ask_ai(text)
        speak(reply)

    except KeyboardInterrupt:
        print("Stopping...")
        break