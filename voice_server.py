# voice_server.py
import time
import os
from dotenv import load_dotenv
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse

from ai_core import chat_with_ai, finalize_call

load_dotenv()

app = Flask(__name__)

def clean(text):
    return (
        text.replace("(", "")
            .replace(")", "")
            .replace("\n", " ")
            .strip()
    )
# ---------------- ENTRY POINT ----------------
@app.route("/voice", methods=["POST"])
def voice():

    resp = VoiceResponse()

    resp.say("Hello! Welcome to QQCRM AI sales assistant.")
    gather = resp.gather(
        input="speech",
        action="/process",
        method="POST",
        speech_timeout="auto",
        language="en-US"
    )

    gather.say(
        "Before we continue, shall I connect you to the CRM AI agent? "
    )

    print("🎧 Waiting for user consent...")

    return str(resp)


# ---------------- MAIN FLOW ----------------
@app.route("/process", methods=["POST"])
def process():

    call_id = request.form.get("CallSid", "user_101")
    user_text = request.form.get("SpeechResult", "").strip()

    resp = VoiceResponse()

    print("\nUSER:", user_text)

    # ---------------- SILENCE HANDLING ----------------
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

    # ---------------- AI CALL ----------------
    start = time.time()
    ai_reply = clean(chat_with_ai(call_id, user_text))
    print("AI TIME:", time.time() - start)
    print("AI:", ai_reply)

    # ---------------- END SIGNAL ----------------
    if ai_reply and "<END_CONVO>" in ai_reply:
        resp.say("Got it. Ending the call now. Goodbye!")
        resp.hangup()
        return str(resp)

    # ---------------- NORMAL FLOW ----------------
    resp.say(ai_reply)

    gather = resp.gather(
        input="speech",
        action="/process",
        method="POST",
        speech_timeout="auto",
        language="en-US"
    )

    print("Listening...")
    # gather.say("Listening...")
    return str(resp)


# ---------------- STATUS + FINALIZATION (REPLACED /end) ----------------
@app.route("/status", methods=["POST"])
def call_status():

    call_status = request.form.get("CallStatus")
    call_id = request.form.get("CallSid", "user_101")

    print("CALL STATUS:", call_status)

    # ✅ FINAL CLEANUP HAPPENS HERE
    if call_status == "completed":

        print("\n📴 CALL ENDED → FINALIZING")

        try:
            result = finalize_call(call_id)

            file_path = f"lead_{call_id}.txt"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"User ID: {call_id}\n")
                f.write(f"Lead Status: {result['lead']}\n\n")

                f.write("=== LEAD SUMMARY ===\n")
                f.write(result["summary"] + "\n\n")

                f.write("=== FULL CONVERSATION ===\n")
                for m in result["conversation"]:
                    f.write(f"{m['role']}: {m['content']}\n")

            print(f"📁 FILE SAVED → {file_path}")

        except Exception as e:
            print("❌ FINALIZATION ERROR:", e)

    return "OK"


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(port=5000, debug=True)