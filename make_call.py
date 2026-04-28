from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

# call = client.calls.create(
#     to=os.getenv("CLIENT_PHONE_NUMBER"),
#     from_=os.getenv("TWILIO_PHONE_NUMBER"),
#     url=os.getenv("NGROK_URL")
# )
call = client.calls.create(
    to=os.getenv("CLIENT_PHONE_NUMBER"),
    from_=os.getenv("TWILIO_PHONE_NUMBER"),
    url=f"{os.getenv('NGROK_URL')}/voice",
    status_callback=f"{os.getenv('NGROK_URL')}/status",
    status_callback_event=[
        "initiated",
        "ringing",
        "answered",
        "completed"
    ],
    status_callback_method="POST"
)