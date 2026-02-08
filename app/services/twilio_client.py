from datetime import datetime
from twilio.rest import Client
from app.config import Config
from app.extensions import db
from app.models import User


def send_whatsapp_message(to_e164: str, message: str):
    """
    Two modes:
    - fake: prints to console only
    - real: sends via Twilio
    """
    mode = Config.WHATSAPP_MODE.lower().strip()

    if mode == "fake":
        print("📨 [FAKE WHATSAPP]")
        print("TO:", to_e164)
        print("MSG:", message)
        print("----")
        return {"mode": "fake", "to": to_e164, "message": message}

    # real mode
    if not Config.TWILIO_ACCOUNT_SID or not Config.TWILIO_AUTH_TOKEN:
        raise Exception("Twilio credentials missing. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.")

    if not Config.TWILIO_WHATSAPP_FROM:
        raise Exception("TWILIO_WHATSAPP_FROM missing, example: whatsapp:+14155238886")

    client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)

    msg = client.messages.create(
        from_=Config.TWILIO_WHATSAPP_FROM,
        to=f"whatsapp:{to_e164}",
        body=message
    )

    return {"mode": "real", "sid": msg.sid}
