import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
# ==============================
# CONFIG
# ==============================
OLLAMA_URL = "http://localhost:11434/api/generate"

BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"

last_update_id = None

# ==============================
# GET UPDATES FROM TELEGRAM
# ==============================
def get_updates():
    global last_update_id

    params = {"timeout": 100}

    if last_update_id is not None:
        params["offset"] = last_update_id + 1

    response = requests.get(BASE_URL + "getUpdates", params=params)
    data = response.json()

    return data.get("result", [])

# ==============================
# SEND MESSAGE TO TELEGRAM
# ==============================
def send_message(chat_id, text):
    requests.post(BASE_URL + "sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

# ==============================
# ASK AI (OLLAMA - LLAMA3)
# ==============================
def ask_ai(prompt):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            }
            #  ,timeout=30   # 🔥 IMPORTANT
        )

        return response.json().get("response", "No response from AI")

    except Exception as e:
        return f"Error contacting AI: {str(e)}"

# ==============================
# MAIN BOT LOOP
# ==============================
def run_bot():
    global last_update_id

    print("🤖 Bot is running...")

    while True:
        try:
            updates = get_updates()

            for update in updates:
                last_update_id = update["update_id"]

                if "message" in update:
                    message = update["message"]

                    # Only handle text messages
                    if "text" in message:
                        chat_id = message["chat"]["id"]
                        user_text = message["text"]

                        print(f"User: {user_text}")

                        # Send to AI
                        ai_reply = ask_ai(user_text)

                        print(f"AI: {ai_reply}")

                        # Reply to user
                        send_message(chat_id, ai_reply)

            time.sleep(1)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)

# ==============================
# START
# ==============================
if __name__ == "__main__":
    run_bot()