import requests
import time

# ==============================
# CONFIG
# ==============================
TOKEN = "8599376063:AAHWPmKLzU6Vv2liqrnAGQv-ys3EEteGwdE"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"
OLLAMA_URL = "http://localhost:11434/api/generate"

last_update_id = None

# Store user modes (for "Ask Anything")
user_mode = {}

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
# SEND INLINE MENU
# ==============================
def send_menu(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "🤖 Interesting", "callback_data": "ai_1"}],
            [{"text": "💬 Productivity Tip", "callback_data": "ai_2"}],
            [{"text": "❓ Ask Anything", "callback_data": "ask"}],
            [{"text": "⚙️ Run Command", "callback_data": "cmd"}]
        ]
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

            # ======================
            # HANDLE BUTTON CLICKS
            # ======================
            if "callback_query" in update:
                query = update["callback_query"]
                chat_id = query["message"]["chat"]["id"]
                data = query["data"]

                print("Button clicked:", data)

                # remove loading animation
                requests.post(BASE_URL + "answerCallbackQuery", json={
                    "callback_query_id": query["id"]
                })

                if data == "ai_1":
                    send_message(chat_id, "🤖 Thinking...")
                    reply = ask_ai("Tell me something interesting")
                    send_message(chat_id, reply)

                elif data == "ai_2":
                    send_message(chat_id, "🤖 Thinking...")
                    reply = ask_ai("Give me a productivity tip")
                    send_message(chat_id, reply)

                elif data == "ask":
                    user_mode[chat_id] = "ask"
                    send_message(chat_id, "❓ Ask me anything...")

                elif data == "cmd":
                    print("Command Executed")  # 🔥 REQUIRED
                    send_message(chat_id, "✅ Command executed successfully!")

            # ======================
            # HANDLE TEXT MESSAGES
            # ======================
            if "message" in update:
                msg = update["message"]

                if "text" in msg:
                    chat_id = msg["chat"]["id"]
                    text = msg["text"]

                    print("User:", text)

                    # start command
                    if text == "/start":
                        # send_message(chat_id, "", {
                        #     "remove_keyboard": True
                        # })
                        send_menu(chat_id)

                    # handle "Ask Anything" mode
                    elif user_mode.get(chat_id) == "ask":
                        send_message(chat_id, "🤖 Thinking...")
                        reply = ask_ai(text)
                        send_message(chat_id, reply)

                        # reset mode (optional)
                        user_mode[chat_id] = None

                    else:
                        send_message(chat_id, "Use /start to open menu.")

        time.sleep(1)

# ==============================
# START
# ==============================
if __name__ == "__main__":
    run_bot()