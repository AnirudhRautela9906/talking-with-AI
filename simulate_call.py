from ai_core import chat_with_ai, classify_lead, generate_summary, sessions

USER_ID = "test_user_101"


# ---------------- DISPLAY HELPERS ----------------
def print_ai(text):
    print("\n🤖 AI:", text)


def print_user(text):
    print("\n🧑 USER:", text)


# ---------------- SIMULATION CORE ----------------
def simulate_user_input(user_text: str):

    print_user(user_text)

    ai_reply = chat_with_ai(USER_ID, user_text)

    print_ai(ai_reply)

    return ai_reply


# ---------------- START ----------------
print("\n🎙️ CRM AI CALL SIMULATOR STARTED\n")
print("Type messages like a real customer. Type 'exit' to end.\n")


# 🔥 FIXED START TRIGGER (NO None ANYMORE)
first_reply = chat_with_ai(
    USER_ID,
    "Start conversation with a new user visiting QQCRM"
)

print_ai(first_reply)


# ---------------- CHAT LOOP ----------------
while True:

    user_input = input("\n🧑 You: ")

    if user_input.lower() in ["exit", "quit", "stop"]:
        break

    ai_reply = simulate_user_input(user_input)

    # ---------------- END CHECK ----------------
    if ai_reply and "<END_CONVO>" in ai_reply:
        print("\n🛑 AI ended conversation")
        break


# ---------------- FINAL ANALYSIS ----------------
print("\n📊 FINAL LEAD ANALYSIS")

lead_status = classify_lead(USER_ID)
summary = generate_summary(USER_ID)

print("\n⭐ Lead Status:", lead_status)

print("\n📝 Summary:\n", summary if summary else "No summary generated")


# ---------------- SAVE RESULT ----------------
file_path = f"lead_{USER_ID}.txt"

with open(file_path, "w", encoding="utf-8") as f:
    f.write(f"User ID: {USER_ID}\n")
    f.write(f"Lead Status: {lead_status}\n\n")

    f.write("=== LEAD SUMMARY ===\n")
    f.write(summary if summary else "No summary generated")
    f.write("\n\n=== FULL CONVERSATION ===\n")

    for m in sessions.get(USER_ID, []):
        f.write(f"{m['role']}: {m['content']}\n")

print(f"\n📁 Lead saved → {file_path}")

print("\n✅ Simulation Complete")