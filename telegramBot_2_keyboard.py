import requests
import time

# ==============================
# CONFIG
# ==============================
TOKEN = "8599376063:AAHWPmKLzU6Vv2liqrnAGQv-ys3EEteGwdE"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"
OLLAMA_URL = "http://localhost:11434/api/generate"

last_update_id = None

# ==============================
# SEND MESSAGE
# ==============================
def send_message(chat_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        data["reply_markup"] = reply_markup

    requests.post(BASE_URL + "sendMessage", json=data)

# ==============================
# SEND MENU
# ==============================
def send_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["🤖 Tell me something interesting"],
            ["💬 Give me a random productivity tip"],
            ["⚙️ Run Command"]
        ],
        "resize_keyboard": True
    }

    send_message(chat_id, "Choose an option:", keyboard)

# ==============================
# GET UPDATES
# ==============================
def get_updates():
    global last_update_id

    params = {"timeout": 100}

    if last_update_id is not None:
        params["offset"] = last_update_id + 1

    res = requests.get(BASE_URL + "getUpdates", params=params)
    return res.json().get("result", [])

# ==============================
# AI FUNCTION
# ==============================
def ask_ai(prompt):
    try:
        res = requests.post(
            OLLAMA_URL,
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            }
        )

        return res.json().get("response", "No response from AI")

    except Exception as e:
        return f"AI Error: {str(e)}"

# ==============================
# MAIN LOOP
# ==============================
def run_bot():
    global last_update_id

    print("🤖 Bot is running...")

    while True:
        updates = get_updates()

        for update in updates:
            last_update_id = update["update_id"]

            if "message" in update:
                msg = update["message"]

                if "text" in msg:
                    chat_id = msg["chat"]["id"]
                    text = msg["text"]

                    print("User:", text)

                    # ======================
                    # HANDLE COMMANDS
                    # ======================
                    if text == "/start":
                        send_menu(chat_id)

                    elif text == "🤖 Tell me something interesting":
                        send_message(chat_id, "🤖 Thinking...")
                        reply = ask_ai("Tell me something interesting")
                        send_message(chat_id, reply)

                    elif text == "💬 Give me a random productivity tip":
                        send_message(chat_id, "🤖 Thinking...")
                        reply = ask_ai("Give me a random productivity tip")
                        send_message(chat_id, reply)

                    elif text == "⚙️ Run Command":
                        print("Command Executed")  # 🔥 YOUR REQUIREMENT
                        send_message(chat_id, "✅ Command executed successfully!")

                    else:
                        send_message(chat_id, "Use the menu options.")

        time.sleep(1)

# ==============================
# START
# ==============================
if __name__ == "__main__":
    run_bot()