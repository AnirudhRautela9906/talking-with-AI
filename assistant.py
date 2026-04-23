import sounddevice as sd
from scipy.io.wavfile import write
from faster_whisper import WhisperModel
import requests
import subprocess
import uuid
import os

# ---------------- CONFIG ----------------
SAMPLE_RATE = 16000
RECORD_SECONDS = 5

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "tinyllama"

PIPER_PATH = "./piper/piper"
VOICE_MODEL = "./voices/en_US-lessac-medium.onnx"

# ---------------- STT ----------------
print("Loading Whisper model...")
whisper = WhisperModel("base", compute_type="int8")

# ---------------- RECORD ----------------
# def record_audio(file="input.wav"):
#     print("🎤 Listening...")

#     audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE),
#                    samplerate=SAMPLE_RATE,
#                    channels=1,
#                    dtype='int16')

#     sd.wait()
#     write(file, SAMPLE_RATE, audio)
#     return file
def record_audio():
    print("🎤 Listening...")

    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='float32'
    )

    sd.wait()
    return audio.flatten()

# ---------------- TRANSCRIBE ----------------
def transcribe(file):
    segments, _ = whisper.transcribe(file)
    return " ".join([s.text for s in segments]).strip()

# ---------------- AI ----------------
messages = [
    {"role": "system", "content": "You are a helpful voice assistant. Keep answers short."}
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
# def speak(text):
#     print("AI:", text)

#     file = f"{uuid.uuid4()}.wav"

#     cmd = f'echo "{text}" | {PIPER_PATH} --model {VOICE_MODEL} --output_file {file}'
#     subprocess.call(cmd, shell=True)

#     os.system(f'aplay {file}')
def speak(text):
    print("AI:", text)

    file = "/tmp/voice_ai_output.wav"

    subprocess.run([
        "./piper/piper",
        "--model",
        "./voices/en_US-lessac-medium.onnx",
        "--output_file",
        file
    ], input=text.encode("utf-8"), check=True)

    subprocess.run(["aplay", file], check=True)

# ---------------- MAIN LOOP ----------------
print("\n🎙️ Offline Voice AI Ready\n")

while True:
    try:
        audio = record_audio()
        text = transcribe(audio)

        if not text:
            continue

        print("You:", text)

        reply = ask_ai(text)
        speak(reply)

    except KeyboardInterrupt:
        print("Stopping...")
        break
