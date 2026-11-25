import hmac
import hashlib
import secrets
import time

from flask import Blueprint, request, jsonify, current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from sms import send_otp_sms

otp_bp = Blueprint("otp", __name__)

OTP_STORE = {}          # phone -> {hash, expires, attempts, last_sent}
OTP_VALID_SECONDS = 300
RESEND_SECONDS = 30
MAX_ATTEMPTS = 5


def _hash(phone, otp):
    key = current_app.config["SECRET_KEY"].encode()
    return hmac.new(key, f"{phone}:{otp}".encode(), hashlib.sha256).hexdigest()


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="phone-verified")


def is_valid_phone(phone):
    return bool(phone) and phone.isdigit() and len(phone) == 10 and phone[0] in "6789"


@otp_bp.route("/api/auth/send-otp", methods=["POST"])
def send_otp():
    phone = (request.get_json() or {}).get("phone", "")
    if not is_valid_phone(phone):
        return jsonify(message="Enter a valid 10-digit mobile number."), 400

    old = OTP_STORE.get(phone)
    if old and time.time() - old["last_sent"] < RESEND_SECONDS:
        wait = int(RESEND_SECONDS - (time.time() - old["last_sent"]))
        return jsonify(message=f"Please wait {wait}s before requesting another OTP."), 429

    otp = str(secrets.randbelow(900000) + 100000)    # 6 digits
    OTP_STORE[phone] = {
        "hash": _hash(phone, otp),
        "expires": time.time() + OTP_VALID_SECONDS,
        "attempts": 0,
        "last_sent": time.time(),
    }
    try:
        send_otp_sms(phone, otp)
    except Exception:
        return jsonify(message="Could not send SMS. Try again later."), 502

    return jsonify(message="OTP sent.")
    return jsonify(error="Enter a valid 10-digit mobile number."), 400
    return jsonify(error=f"Please wait {wait}s before requesting another OTP."), 429
    return jsonify(error="Could not send SMS. Try again later."), 502
    return jsonify(error="Request an OTP first."), 400
    return jsonify(error="OTP expired. Request a new one."), 400
    return jsonify(error="Too many wrong attempts. Request a new OTP."), 429
    return jsonify(error="Wrong OTP."), 400


@otp_bp.route("/api/auth/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json() or {}
    phone, otp = data.get("phone", ""), data.get("otp", "")

    rec = OTP_STORE.get(phone)
    if not rec:
        return jsonify(message="Request an OTP first."), 400
    if time.time() > rec["expires"]:
        OTP_STORE.pop(phone, None)
        return jsonify(message="OTP expired. Request a new one."), 400
    if rec["attempts"] >= MAX_ATTEMPTS:
        return jsonify(message="Too many wrong attempts. Request a new OTP."), 429

    if not hmac.compare_digest(rec["hash"], _hash(phone, otp)):
        rec["attempts"] += 1
        return jsonify(message="Wrong OTP."), 400

    OTP_STORE.pop(phone, None)
    token = _serializer().dumps({"phone": phone})
    return jsonify(message="Verified.", otp_token=token)


def phone_is_verified(token, phone):
    """Call this inside /api/auth/register."""
    try:
        data = _serializer().loads(token, max_age=1800)   # valid 30 minutes
    except (BadSignature, SignatureExpired):
        return False
    return data.get("phone") == phone