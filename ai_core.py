# ai_core.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3"
MAX_HISTORY = 20

sessions = {}
empty_count = {}

# ---------------- LOAD PROMPT ----------------
with open("CRM_Script.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

COMPANY_TOOL_NAME = os.getenv("COMPANY_TOOL_NAME", "COMPANY_TOOL_NAME")
SYSTEM_PROMPT = SYSTEM_PROMPT.replace("COMPANY_TOOL_NAME", COMPANY_TOOL_NAME)


# ---------------- SAFE INIT ----------------
def _init_user(user_id):
    if user_id not in sessions:
        sessions[user_id] = []
        empty_count[user_id] = 0


# ---------------- CHAT CORE ----------------
def chat_with_ai(user_id: str, user_message: str | None):

    _init_user(user_id)

    # ---------------- SILENCE HANDLING ----------------
    if user_message is None or str(user_message).strip() == "":
        empty_count[user_id] += 1

        if empty_count[user_id] == 2:
            return "Just checking, are you still there?"

        if empty_count[user_id] >= 3:
            return "Looks like you're unavailable right now. I'll follow up later. Have a great day! <END_CONVO>"

        return ""

    empty_count[user_id] = 0

    sessions[user_id].append({"role": "user", "content": user_message})

    try:
        res = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                *sessions[user_id]
            ],
            "stream": False
        }, timeout=30)

        data = res.json()
        reply = data["message"]["content"]

    except Exception as e:
        print("❌ CHAT ERROR:", e)
        reply = "Sorry, I'm having trouble responding right now."

    sessions[user_id].append({"role": "assistant", "content": reply})
    sessions[user_id] = sessions[user_id][-MAX_HISTORY:]

    return reply


# ---------------- LEAD CLASSIFICATION ----------------
def classify_lead(user_id: str):

    chat = sessions.get(user_id, [])
    if not chat:
        return "Unknown"

    text = "\n".join([f"{m['role']}: {m['content']}" for m in chat])

    try:
        res = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "Return ONLY one word: Hot, Warm, Cold."},
                {"role": "user", "content": text}
            ],
            "stream": False
        }, timeout=20)

        data = res.json()
        result = data["message"]["content"].strip()

        # SAFE PARSE
        for label in ["Hot", "Warm", "Cold"]:
            if label.lower() in result.lower():
                return label

        return "Unknown"

    except Exception:
        return "Unknown"


# ---------------- SUMMARY ----------------
def generate_summary(user_id: str):

    chat = sessions.get(user_id, [])
    if not chat:
        return "No summary generated"

    text = "\n".join([f"{m['role']}: {m['content']}" for m in chat])

    try:
        res = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "Summarize in bullet points only."},
                {"role": "user", "content": text}
            ],
            "stream": False
        }, timeout=30)

        data = res.json()
        return data["message"]["content"]

    except Exception as e:
        print("❌ SUMMARY ERROR:", e)
        return "Summary generation failed"


# ---------------- FINAL PIPELINE ----------------
def finalize_call(user_id: str):

    lead = classify_lead(user_id)
    summary = generate_summary(user_id)
    conversation = sessions.get(user_id, [])

    return {
        "lead": lead,
        "summary": summary,
        "conversation": conversation
    }