import os
import threading
import time
from dotenv import load_dotenv
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse

from ai_core import chat_with_ai, finalize_call

load_dotenv()

app = Flask(__name__)

# ---------------- STATE ----------------
warmup_done = set()
lock = threading.Lock()


# ---------------- AI WARMUP ----------------
def warm_ai():
    try:
        print("🔥 WARMING UP AI MODEL...")

        # preload model into memory / KV cache
        chat_with_ai("warmup", "hello")

        print("✅ AI WARMED UP")

    except Exception as e:
        print("❌ WARMUP ERROR:", e)


# ---------------- CLEAN TEXT ----------------
def clean(text):
    return (
        text.replace("(", "")
            .replace(")", "")
            .replace("\n", " ")
            .strip()
    )


# ---------------- VOICE ENTRY ----------------
@app.route("/voice", methods=["POST"])
def voice():

    call_id = request.form.get("CallSid")

    # 🔥 warm immediately (safe per-call)
    with lock:
        if call_id not in warmup_done:
            warmup_done.add(call_id)
            threading.Thread(target=warm_ai, daemon=True).start()

    resp = VoiceResponse()

    resp.say("Hello! Welcome to QQCRM AI sales assistant.")

    gather = resp.gather(
        input="speech",
        action="/process",
        method="POST",
        speech_timeout="auto",
        language="en-US"
    )

    gather.say("Before we continue, shall I connect you to the QQCRM AI agent?")

    print("🎧 Call started, waiting for user...")

    return str(resp)


# ---------------- MAIN FLOW ----------------
@app.route("/process", methods=["POST"])
def process():

    call_id = request.form.get("CallSid")
    user_text = request.form.get("SpeechResult", "").strip()

    resp = VoiceResponse()

    print("\nUSER:", user_text)

    # ---------------- SILENCE ----------------
    if not user_text:
        gather = resp.gather(
            input="speech",
            action="/process",
            method="POST",
            speech_timeout="auto",
            language="en-US"
        )
        gather.say("I didn't catch that. Please speak again.")
        return str(resp)

    # ---------------- AI RESPONSE ----------------
    start = time.time()
    ai_reply = clean(chat_with_ai(call_id, user_text))
    print("AI TIME:", time.time() - start)
    print("AI:", ai_reply)

    # ---------------- END CALL ----------------
    if "<END_CONVO>" in ai_reply:
        resp.say("Got it. Ending the call now. Goodbye!")
        resp.hangup()
        return str(resp)

    # ---------------- SPEAK AI ----------------
    resp.say(ai_reply)

    gather = resp.gather(
        input="speech",
        action="/process",
        method="POST",
        speech_timeout="auto",
        language="en-US"
    )

    print("Listening...")

    return str(resp)


# ---------------- CALL STATUS ----------------
@app.route("/status", methods=["POST"])
def call_status():

    call_status_value = request.form.get("CallStatus")
    call_id = request.form.get("CallSid", "user_101")

    print("CALL STATUS:", call_status_value)

    # ---------------- FINAL CLEANUP ----------------
    if call_status_value == "completed":

        print("\n📴 CALL ENDED → FINALIZING")

        try:
            result = finalize_call(call_id)

            # ---------------- CREATE FOLDER ----------------
            folder_path = "client_summary"
            os.makedirs(folder_path, exist_ok=True)

            # ---------------- FILE PATH ----------------
            file_path = os.path.join(folder_path, f"lead_{call_id}.txt")

            # ---------------- WRITE FILE ----------------
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"Call ID: {call_id}\n")
                f.write(f"Lead Status: {result['lead']}\n\n")

                f.write("=== SUMMARY ===\n")
                f.write(result["summary"] + "\n\n")

                f.write("=== CONVERSATION ===\n")
                for m in result["conversation"]:
                    f.write(f"{m['role']}: {m['content']}\n")

            print(f"📁 SAVED → {file_path}")

        except Exception as e:
            print("❌ FINALIZATION ERROR:", e)

        # ---------------- CLEANUP ----------------
        with lock:
            warmup_done.discard(call_id)

    return "OK"

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(port=5000, debug=True)