"""Endpoints that Twilio calls. Every request must carry a valid Twilio signature."""
from __future__ import annotations

from flask import Blueprint, Response, abort, current_app, request
from xml.sax.saxutils import escape

from . import services, sms

bp = Blueprint("webhooks", __name__, url_prefix="/twilio")


def _require_signature():
    if not sms.validate_twilio_request(request):
        current_app.logger.warning("Rejected unsigned/invalid Twilio webhook from %s", request.remote_addr)
        abort(403)


def _twiml(reply: str | None) -> Response:
    inner = f"<Message>{escape(reply)}</Message>" if reply else ""
    return Response(f'<?xml version="1.0" encoding="UTF-8"?><Response>{inner}</Response>',
                    mimetype="text/xml")


@bp.post("/inbound")
def inbound():
    """Configure in Twilio: Phone Number → Messaging → 'A message comes in' → this URL (HTTP POST)."""
    _require_signature()
    from_phone = request.form.get("From", "")
    if not sms.E164.match(from_phone):
        return _twiml(None)
    reply = services.handle_inbound(from_phone, request.form.get("Body", ""), request.form.get("MessageSid", ""))
    return _twiml(reply)


@bp.post("/status")
def status():
    """Twilio posts delivery updates here (set automatically as each message's StatusCallback)."""
    _require_signature()
    sid = request.form.get("MessageSid", "")
    new_status = request.form.get("MessageStatus", "")
    if sid and new_status:
        services.apply_status_update(sid, new_status, request.form.get("ErrorCode") or None,
                                     request.form.get("ErrorMessage") or None)
    return ("", 204)
