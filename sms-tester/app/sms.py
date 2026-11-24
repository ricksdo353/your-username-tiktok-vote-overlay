"""Twilio integration, phone/number helpers and message rendering.

The Twilio client lives only on the server. Credentials never leave this module.
"""
from __future__ import annotations

import re
import secrets
from dataclasses import dataclass

from flask import current_app

from .config import Settings

E164 = re.compile(r"^\+[1-9]\d{7,14}$")

# Twilio statuses that will not change any more.
FINAL_STATUSES = {"delivered", "undelivered", "failed", "received", "read", "canceled", "blocked"}
STATUS_ORDER = ["queued_local", "accepted", "queued", "sending", "sent", "delivered", "read"]

GSM7 = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
GSM7_EXT = set("^{}\\[~]|€\f")


def normalize_phone(raw: str, default_country_code: str = "") -> str | None:
    """Return the number in +E.164 form, or None if it is not a valid number."""
    cleaned = re.sub(r"[\s().\-]", "", raw or "")
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if not cleaned.startswith("+") and default_country_code and cleaned.isdigit():
        cleaned = "+" + default_country_code + cleaned.lstrip("0")
    return cleaned if E164.match(cleaned) else None


def mask_phone(phone: str) -> str:
    return phone[:-4].rstrip() + "••" + phone[-2:] if len(phone) > 6 else phone


def segment_info(body: str) -> tuple[str, int]:
    """Return (encoding, number of SMS segments) — mirrors how carriers bill."""
    if all(c in GSM7 or c in GSM7_EXT for c in body):
        length = sum(2 if c in GSM7_EXT else 1 for c in body)
        return "GSM-7", 1 if length <= 160 else -(-length // 153)
    units = len(body.encode("utf-16-le")) // 2
    return "UCS-2", 1 if units <= 70 else -(-units // 67)


def render_body(template_body: str, recipient_name: str, settings: Settings, now_local) -> str:
    """Fill in the small, fixed set of placeholders. Unknown {braces} are left as-is."""
    first = (recipient_name or "").split(" ")[0] or "there"
    values = {
        "{name}": recipient_name or "there",
        "{first_name}": first,
        "{date}": now_local.strftime("%b %d"),
        "{time}": now_local.strftime("%H:%M"),
        "{app_name}": settings.app_name,
    }
    out = template_body
    for key, val in values.items():
        out = out.replace(key, val)
    return out.strip()


def with_footer(body: str, settings: Settings) -> str:
    if settings.append_opt_out_footer and "stop" not in body.lower():
        return f"{body}\nReply STOP to opt out."
    return body


def optin_request_text(settings: Settings) -> str:
    return (
        f"{settings.app_name}: you were added as a test recipient. Reply YES to agree to receive "
        "occasional test texts. Msg & data rates may apply. Reply STOP to opt out, HELP for help."
    )


def optin_confirmed_text(settings: Settings) -> str:
    return f"{settings.app_name}: thanks, you're confirmed for test messages. Reply STOP anytime to opt out."


@dataclass
class SendResult:
    ok: bool
    sid: str | None = None
    status: str = "failed"
    error_code: str | None = None
    error_message: str | None = None


def _client():
    from twilio.rest import Client  # imported lazily so dry-run works without network

    s: Settings = current_app.config["SETTINGS"]
    return Client(s.twilio_account_sid, s.twilio_auth_token)


def send_sms(to: str, body: str) -> SendResult:
    s: Settings = current_app.config["SETTINGS"]
    if not s.is_live:
        return SendResult(ok=True, sid="SM" + "dry" + secrets.token_hex(15), status="delivered")

    from twilio.base.exceptions import TwilioRestException

    params = {"to": to, "body": body}
    if s.twilio_messaging_service_sid:
        params["messaging_service_sid"] = s.twilio_messaging_service_sid
    else:
        params["from_"] = s.twilio_from_number
    if s.public_base_url:
        params["status_callback"] = f"{s.public_base_url}/twilio/status"
    try:
        msg = _client().messages.create(**params)
        return SendResult(ok=True, sid=msg.sid, status=msg.status or "queued")
    except TwilioRestException as exc:
        current_app.logger.warning("Twilio error %s: %s", exc.code, exc.msg)
        return SendResult(ok=False, error_code=str(exc.code or exc.status), error_message=str(exc.msg)[:300])
    except Exception as exc:  # network errors etc.
        current_app.logger.exception("Unexpected error sending SMS")
        return SendResult(ok=False, error_code="network", error_message=str(exc)[:300])


def fetch_status(sid: str) -> SendResult | None:
    """Ask Twilio for the current status of a message (used when webhooks are not configured)."""
    s: Settings = current_app.config["SETTINGS"]
    if not s.is_live or not sid.startswith(("SM", "MM")):
        return None
    try:
        msg = _client().messages(sid).fetch()
    except Exception:
        current_app.logger.exception("Could not fetch status for %s", sid)
        return None
    return SendResult(
        ok=True,
        sid=sid,
        status=msg.status,
        error_code=str(msg.error_code) if msg.error_code else None,
        error_message=msg.error_message,
    )


def validate_twilio_request(request) -> bool:
    """Check X-Twilio-Signature so only Twilio can call the webhooks."""
    s: Settings = current_app.config["SETTINGS"]
    signature = request.headers.get("X-Twilio-Signature", "")
    if not s.twilio_auth_token or not signature:
        return False
    from twilio.request_validator import RequestValidator

    if s.public_base_url:
        url = s.public_base_url + request.full_path.rstrip("?")
    else:
        url = request.url
    return RequestValidator(s.twilio_auth_token).validate(url, request.form.to_dict(), signature)
