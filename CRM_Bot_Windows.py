import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import requests
import subprocess
import uuid
import os
import queue
import time
import winsound
from dotenv import load_dotenv

load_dotenv()

COMPANY_TOOL_NAME = os.getenv("COMPANY_TOOL_NAME")

# ---------------- FOLDERS ----------------
AUDIO_DIR = "audio_outputs"
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

# ---------------- CONFIG ----------------
SAMPLE_RATE = 16000
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3"

PIPER_PATH = "./piper_windows/piper.exe"
VOICE_MODEL = "./voices/en_US-lessac-medium.onnx"

SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 2

MAX_EMPTY = 3
MAX_HISTORY = 20
MAX_AUDIO_FILES = 10

# ---------------- LOAD CRM SCRIPT ----------------
with open("CRM_Script.txt", "r") as f:
    SYSTEM_PROMPT = f.read()

SYSTEM_PROMPT = SYSTEM_PROMPT.replace("COMPANY_TOOL_NAME", COMPANY_TOOL_NAME)

# ---------------- SESSION ----------------
sessions = {}

# ---------------- STT ----------------
print("Loading Whisper model...")
whisper = WhisperModel("base", device="cpu", compute_type="int8")

# ---------------- AUDIO STREAM ----------------
audio_queue = queue.Queue()

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
                    print("🛑 Silence detected")
                    break
            else:
                silence_start = None

    return np.concatenate(recorded_audio).flatten()

# ---------------- TRANSCRIBE ----------------
def transcribe(audio):
    segments, _ = whisper.transcribe(audio, language="en")
    return " ".join([s.text for s in segments]).strip()

# ---------------- AI CHAT ----------------
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

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=15)
        data = response.json()
    except Exception as e:
        print("⚠️ API Error:", e)
        return "Sorry, something went wrong."

    if "message" not in data:
        print("⚠️ Ollama error:", data)
        return "Sorry, something went wrong."

    reply = data["message"]["content"]

    sessions[user_id].append({"role": "assistant", "content": reply})

    # trim history
    sessions[user_id] = sessions[user_id][-MAX_HISTORY:]

    return reply

# ---------------- INTENT DETECTION ----------------
def should_end_conversation(text):
    text = text.lower()

    STOP_KEYWORDS = [
        "not interested", "no thanks", "no thank you",
        "thanks", "thank you", "thank you very much",
        "ok thanks", "okay thanks",
        "that's all", "i'm done", "done",
        "bye", "goodbye", "see you",
        "talk later", "call me later",
        "don't call", "end call", "stop"
    ]

    return any(k in text for k in STOP_KEYWORDS)

# ---------------- CLEAN AUDIO ----------------
def cleanup_audio():
    files = sorted(os.listdir(AUDIO_DIR))
    if len(files) > MAX_AUDIO_FILES:
        os.remove(os.path.join(AUDIO_DIR, files[0]))

# ---------------- TTS ----------------
def speak(text):
    # 🔥 remove token before speaking
    clean_text = text.replace("<END_CONVO>", "").strip()

    print("🤖 AI:", clean_text)

    file = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.wav")

    subprocess.run([
        PIPER_PATH,
        "--model",
        VOICE_MODEL,
        "--output_file",
        file
    ], input=clean_text.encode("utf-8"), check=True)

    winsound.PlaySound(file, winsound.SND_FILENAME)
# ---------------- CLASSIFY LEAD ----------------
def classify_lead(user_id):
    conversation = sessions.get(user_id, [])

    if not conversation:
        return "Unknown"

    chat_text = "\n".join([f"{m['role']}: {m['content']}" for m in conversation])

    prompt = f"""
Classify the lead into ONE word ONLY:

Hot
Warm
Cold

Reply ONLY with one word.

Conversation:
{chat_text}
"""

    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are a CRM expert."},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }, timeout=15)

        data = response.json()
    except Exception:
        return "Unknown"

    if "message" not in data:
        return "Unknown"

    return data["message"]["content"].strip().split()[0]

# ---------------- SUMMARIZE LEAD ----------------
def generate_summary(user_id):
    conversation = sessions.get(user_id, [])

    chat_text = "\n".join([
        f"{m['role']}: {m['content']}" for m in conversation
    ])

    prompt = f"""
Summarize this sales conversation in SIMPLE BULLET POINTS ONLY.

Rules:
- No JSON
- No formatting symbols
- No headings except "Lead Summary:"
- Keep it short and human-readable
- Focus on business insights only

Output format:

Lead Summary:
- point 1
- point 2
- point 3
- point 4

Now analyze:

{chat_text}
"""

    response = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a sales analyst."},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    })

    data = response.json()

    if "message" not in data:
        return {}

    return data["message"]["content"]

# ---------------- SAVE LEAD ----------------
def save_lead(user_id, lead_status):
    file_path = f"lead_{user_id}.txt"
    conversation = sessions.get(user_id, [])

    summary = generate_summary(user_id)

    # If LLM returns something messy, keep it safe
    if not summary:
        summary = "Lead Summary:\n- No summary generated"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"User ID: {user_id}\n")
        f.write(f"Lead Status: {lead_status}\n\n")

        f.write("=== LEAD SUMMARY ===\n")
        f.write(summary.strip() + "\n\n") 

        f.write("=== FULL CONVERSATION ===\n")
        for msg in conversation:
            f.write(f"{msg['role']}: {msg['content']}\n")

    print(f"📁 Lead saved with summary → {file_path}")

# ---------------- MAIN ----------------
print(f"\n🎙️ {COMPANY_TOOL_NAME} Voice AI Sales Agent Ready\n")

user_id = "user_101"
EMPTY_COUNT = 0

# Start conversation
reply = chat_with_ai(user_id, f"Start conversation with a new user visiting {COMPANY_TOOL_NAME}")
speak(reply)

while True:
    try:
        audio = record_until_silence()
        text = transcribe(audio)

        if not text:
            EMPTY_COUNT += 1
            print(f"⚠️ No speech detected ({EMPTY_COUNT}/{MAX_EMPTY})")

            if EMPTY_COUNT == 2:
                speak("Just checking, are you still there?")

            if EMPTY_COUNT >= MAX_EMPTY:
                speak("Looks like you're unavailable right now. I'll follow up later. Have a great day!")

                lead_status = classify_lead(user_id)
                save_lead(user_id, lead_status)
                break

            continue
        else:
            EMPTY_COUNT = 0

        print("📝 You:", text)

        # 🔥 HARD EXIT (NO AI CALL)
        if should_end_conversation(text):
            speak("No problem. Thanks for your time. Have a great day!")

            lead_status = classify_lead(user_id)
            speak(f"You are marked as a {lead_status} lead.")

            save_lead(user_id, lead_status)
            break

        # Normal flow
        reply = chat_with_ai(user_id, text)
        speak(reply)

        # ✅ NEW: detect end signal from AI
        if "<END_CONVO>" in reply:
            print("🛑 AI ended conversation")

            lead_status = classify_lead(user_id)
            speak(f"You are marked as a {lead_status} lead.")

            save_lead(user_id, lead_status)
            break
    except KeyboardInterrupt:
        print("\nStopping...")
        break