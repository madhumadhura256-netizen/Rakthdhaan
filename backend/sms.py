import os
import requests

PROVIDER = os.getenv("SMS_PROVIDER", "console")   # console | fast2sms | twilio


def send_otp_sms(phone, otp):
    if PROVIDER == "fast2sms":
        r = requests.post(
            "https://www.fast2sms.com/dev/bulkV2",
            headers={"authorization": os.environ["FAST2SMS_KEY"]},
            json={"route": "otp", "variables_values": otp, "numbers": phone},
            timeout=10,
        )
        r.raise_for_status()
    else:
        send_sms(phone, f"Raktdhan OTP: {otp}. Valid for 5 minutes.")


def send_sms(phone, text):
    if PROVIDER == "fast2sms":
        r = requests.post(
            "https://www.fast2sms.com/dev/bulkV2",
            headers={"authorization": os.environ["FAST2SMS_KEY"]},
            json={"route": "q", "message": text, "numbers": phone},
            timeout=10,
        )
        r.raise_for_status()

    elif PROVIDER == "twilio":
        from twilio.rest import Client
        client = Client(os.environ["TWILIO_SID"], os.environ["TWILIO_TOKEN"])
        client.messages.create(
            body=text,
            from_=os.environ["TWILIO_FROM"],
            to="+91" + phone,
        )

    else:
        # Demo mode: just print it
        print(f"[SMS to {phone}] {text}")