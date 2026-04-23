import sounddevice as sd
from faster_whisper import WhisperModel
import requests
import subprocess
import uuid
import os
import numpy as np
from scipy.io.wavfile import write

# ---------------- CONFIG ----------------
SAMPLE_RATE = 16000
RECORD_SECONDS = 5

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3"

PIPER_PATH = "./piper/piper"
VOICE_MODEL = "./voices/en_US-lessac-medium.onnx"

# ---------------- LOAD CRM SCRIPT ----------------
with open("CRM_Script.txt", "r") as f:
    SYSTEM_PROMPT = f.read()

# ---------------- SESSION MEMORY ----------------
sessions = {}

# ---------------- STT ----------------
print("Loading Whisper model...")
whisper = WhisperModel("base", compute_type="int8")

# ---------------- RECORD ----------------

def record_audio():
    print("🎤 Listening...")

    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='int16'   # IMPORTANT
    )

    sd.wait()

    file = "/tmp/input.wav"
    write(file, SAMPLE_RATE, audio)

    return file

# ---------------- TRANSCRIBE ----------------
def transcribe(file):
    segments, _ = whisper.transcribe(file)
    return " ".join([s.text for s in segments]).strip()

# ---------------- AI (CRM SALES AGENT) ----------------
def chat_with_ai(user_id, user_message):

    if user_id not in sessions:
        sessions[user_id] = []

    sessions[user_id].append({"role": "user", "content": user_message})

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *sessions[user_id]
        ],
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=payload)
    data = response.json()

    if "message" not in data:
        print("⚠️ Ollama error:", data)
        return "Sorry, something went wrong."

    reply = data["message"]["content"]

    sessions[user_id].append({"role": "assistant", "content": reply})

    # limit memory
    if len(sessions[user_id]) > 20:
        sessions[user_id].pop(0)

    return reply

# ---------------- TTS ----------------
def speak(text):
    print("🤖 AI:", text)

    file = f"/tmp/{uuid.uuid4()}.wav"

    subprocess.run([
        PIPER_PATH,
        "--model",
        VOICE_MODEL,
        "--output_file",
        file
    ], input=text.encode("utf-8"), check=True)

    subprocess.run(["aplay", file], check=True)


# ---------------- Classify Lead ----------------
def classify_lead(user_id):
    conversation = sessions.get(user_id, [])

    if not conversation:
        return "Unknown"

    # Convert conversation to text
    chat_text = "\n".join([f"{m['role']}: {m['content']}" for m in conversation])

    prompt = f"""
Analyze the following conversation between AI sales agent and user.

Classify the lead into one of:
- Hot (ready to buy / asking pricing / demo)
- Warm (interested but not ready)
- Cold (just exploring / not interested)

Conversation:
{chat_text}

Reply ONLY with one word: Hot / Warm / Cold
"""

    response = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a CRM lead scoring expert."},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    })

    data = response.json()

    if "message" not in data:
        return "Unknown"

    result = data["message"]["content"].strip()

    return result

# ---------------- Save Lead ----------------
def save_lead(user_id, lead_status):
    file_path = f"lead_{user_id}.txt"

    conversation = sessions.get(user_id, [])

    with open(file_path, "w") as f:
        f.write(f"User ID: {user_id}\n")
        f.write(f"Lead Status: {lead_status}\n\n")
        f.write("Conversation:\n")

        for msg in conversation:
            f.write(f"{msg['role']}: {msg['content']}\n")

    print(f"📁 Lead saved to {file_path}")


# ---------------- MAIN LOOP ----------------
print("\n🎙️ ZZCRM Voice AI Sales Agent Ready\n")

user_id = "user_101"

# 🔥 AI starts conversation
first_message = "Start conversation with a new user visiting ZZCRM website."

reply = chat_with_ai(user_id, first_message)
speak(reply)

while True:
    try:
        audio_file = record_audio()
        text = transcribe(audio_file)

        if not text:
            continue

        print("📝 You:", text)

        # if text.lower() in ["exit", "quit", "stop"]:
        #     speak("Goodbye! 👋")
        #     break

        # reply = chat_with_ai(user_id, text)

        # speak(reply)
        STOP_WORDS = ["exit", "quit", "stop", "bye", "goodbye", "end call"]

        clean_text = text.lower().strip()

        if any(word in clean_text for word in STOP_WORDS):
            speak("Thanks for your time. Let me evaluate your requirements.")

            lead_status = classify_lead(user_id)

            speak(f"You are marked as a {lead_status} lead. Our team may follow up with you.")

            save_lead(user_id, lead_status)

            break

        # 🔥 NORMAL FLOW
        reply = chat_with_ai(user_id, text)
        speak(reply)    

    except KeyboardInterrupt:
        print("\nStopping...")
        break