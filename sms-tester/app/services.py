"""Business rules: consent, rate limits, sending, inbound keywords.

Every outbound SMS goes through `_reserve_and_send`, which checks all limits
and reserves the slot inside one SQLite write transaction, so two taps on the
Send button (or two server threads) can never exceed a limit.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta

from flask import current_app

from . import sms
from .config import Settings
from .db import audit, get_db, get_setting, iso, now_iso, utcnow

OPT_OUT_WORDS = {"STOP", "STOPALL", "UNSUBSCRIBE", "CANCEL", "END", "QUIT", "OPTOUT", "OPT-OUT", "REVOKE"}
OPT_IN_WORDS = {"YES", "Y", "START", "UNSTOP", "SUBSCRIBE"}
HELP_WORDS = {"HELP", "INFO"}

_send_lock = threading.Lock()


class SendBlocked(Exception):
    """A send was refused by a safety rule. The message is shown to the user."""


def settings() -> Settings:
    return current_app.config["SETTINGS"]


def sending_enabled() -> bool:
    return get_setting("sending_enabled", "1") == "1"


def local_now() -> datetime:
    return utcnow().astimezone(settings().timezone)


def start_of_local_day_utc() -> str:
    now = local_now()
    return iso(now.replace(hour=0, minute=0, second=0, microsecond=0))


# ---------------------------------------------------------------- limits

def _count(db, sql: str, params: tuple) -> int:
    return db.execute(sql, params).fetchone()[0]


def _check_limits(db, recipient, body: str, kind: str) -> None:
    s = settings()
    now = utcnow()
    counted = "direction = 'outbound' AND status NOT IN ('failed')"

    sent_today = _count(db, f"SELECT COUNT(*) FROM messages WHERE {counted} AND created_at >= ?",
                        (start_of_local_day_utc(),))
    if sent_today >= s.global_daily_limit:
        raise SendBlocked(f"Daily limit reached ({s.global_daily_limit} messages). Resets at midnight.")

    last_minute = _count(db, f"SELECT COUNT(*) FROM messages WHERE {counted} AND created_at >= ?",
                         (iso(now - timedelta(minutes=1)),))
    if last_minute >= s.global_per_minute_limit:
        raise SendBlocked(f"Slow down: at most {s.global_per_minute_limit} messages per minute.")

    if kind != "test":
        return  # opt-in requests have their own, stricter limits

    counted += " AND kind = 'test'"  # per-recipient limits apply to test messages

    to_recipient_today = _count(
        db, f"SELECT COUNT(*) FROM messages WHERE {counted} AND recipient_id = ? AND created_at >= ?",
        (recipient["id"], start_of_local_day_utc()),
    )
    if to_recipient_today >= s.recipient_daily_limit:
        raise SendBlocked(f"This recipient already got {s.recipient_daily_limit} messages today.")

    last = db.execute(
        f"SELECT created_at FROM messages WHERE {counted} AND recipient_id = ? ORDER BY id DESC LIMIT 1",
        (recipient["id"],),
    ).fetchone()
    if last:
        elapsed = (now - datetime.fromisoformat(last["created_at"].replace("Z", "+00:00"))).total_seconds()
        wait = s.recipient_min_interval_seconds - int(elapsed)
        if wait > 0:
            raise SendBlocked(f"Please wait {wait}s before messaging this recipient again.")

    if s.duplicate_window_minutes:
        dup = _count(
            db, f"SELECT COUNT(*) FROM messages WHERE {counted} AND recipient_id = ? AND body = ? AND created_at >= ?",
            (recipient["id"], body, iso(now - timedelta(minutes=s.duplicate_window_minutes))),
        )
        if dup:
            raise SendBlocked(f"Same text was sent to this recipient in the last {s.duplicate_window_minutes} min.")


def _reserve_and_send(recipient, body: str, kind: str) -> int:
    """Check limits, record the message, send it via Twilio and store the result."""
    db = get_db()
    with _send_lock:
        db.execute("BEGIN IMMEDIATE")
        try:
            if not sending_enabled():
                raise SendBlocked("Sending is STOPPED. Tap START on the dashboard to resume.")
            _check_limits(db, recipient, body, kind)
            ts = now_iso()
            cur = db.execute(
                "INSERT INTO messages(recipient_id, phone, direction, kind, body, status, created_at, updated_at) "
                "VALUES (?, ?, 'outbound', ?, ?, 'queued_local', ?, ?)",
                (recipient["id"], recipient["phone"], kind, body, ts, ts),
            )
            message_id = cur.lastrowid
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise

    result = sms.send_sms(recipient["phone"], body)
    db.execute(
        "UPDATE messages SET twilio_sid = ?, status = ?, error_code = ?, error_message = ?, updated_at = ? WHERE id = ?",
        (result.sid, result.status if result.ok else "failed", result.error_code, result.error_message,
         now_iso(), message_id),
    )
    if not result.ok and result.error_code == "21610":
        # Twilio says this number has replied STOP — record it so we never try again.
        _mark_opted_out(recipient["id"], "twilio:21610")
    if not result.ok:
        raise SendBlocked(f"Twilio refused the message: {result.error_message or result.error_code}")
    return message_id


# ---------------------------------------------------------------- outbound flows

def send_test_message(recipient_id: int, body: str) -> int:
    s = settings()
    db = get_db()
    recipient = db.execute("SELECT * FROM recipients WHERE id = ?", (recipient_id,)).fetchone()
    if recipient is None:
        raise SendBlocked("Recipient not found.")
    if recipient["status"] == "opted_out":
        raise SendBlocked("This recipient opted out (STOP). They must text START to opt back in.")
    if recipient["status"] != "consented":
        raise SendBlocked("This recipient has not confirmed consent yet (they need to reply YES).")
    if recipient["paused"]:
        raise SendBlocked("This recipient is paused. Resume them first.")

    body = sms.render_body(body, recipient["name"], s, local_now())
    if not body:
        raise SendBlocked("Message is empty.")
    body = sms.with_footer(body, s)
    if len(body) > s.max_body_chars:
        raise SendBlocked(f"Message is too long ({len(body)} of max {s.max_body_chars} characters).")

    message_id = _reserve_and_send(recipient, body, "test")
    audit("send", f"message #{message_id} to recipient #{recipient_id}")
    return message_id


def send_optin_request(recipient_id: int) -> int:
    s = settings()
    db = get_db()
    recipient = db.execute("SELECT * FROM recipients WHERE id = ?", (recipient_id,)).fetchone()
    if recipient is None:
        raise SendBlocked("Recipient not found.")
    if recipient["status"] != "pending":
        raise SendBlocked("Consent requests can only be sent to recipients who are still pending.")
    if not recipient["attested_at"]:
        raise SendBlocked("Confirm the person agreed to be contacted before sending a consent request.")
    if recipient["optin_requests"] >= s.optin_max_requests:
        raise SendBlocked(f"Already asked {s.optin_max_requests} times with no reply. "
                          "Ask the person directly to text YES to your Twilio number.")
    if recipient["last_optin_request_at"]:
        last = datetime.fromisoformat(recipient["last_optin_request_at"].replace("Z", "+00:00"))
        next_ok = last + timedelta(hours=s.optin_cooldown_hours)
        if utcnow() < next_ok:
            hours = max(1, round((next_ok - utcnow()).total_seconds() / 3600))
            raise SendBlocked(f"A consent request was sent recently. You can ask again in ~{hours}h.")

    message_id = _reserve_and_send(recipient, sms.optin_request_text(s), "optin")
    db.execute(
        "UPDATE recipients SET optin_requests = optin_requests + 1, last_optin_request_at = ? WHERE id = ?",
        (now_iso(), recipient_id),
    )
    audit("optin_request", f"recipient #{recipient_id}")
    return message_id


# ---------------------------------------------------------------- consent state

def _mark_opted_out(recipient_id: int, evidence: str) -> None:
    get_db().execute(
        "UPDATE recipients SET status = 'opted_out', opted_out_at = ?, consent_evidence = ? WHERE id = ?",
        (now_iso(), evidence, recipient_id),
    )
    audit("opt_out", f"recipient #{recipient_id} via {evidence}")


def _mark_consented(recipient_id: int, evidence: str) -> None:
    get_db().execute(
        "UPDATE recipients SET status = 'consented', consent_confirmed_at = ?, consent_evidence = ?, "
        "opted_out_at = NULL WHERE id = ?",
        (now_iso(), evidence, recipient_id),
    )
    audit("opt_in", f"recipient #{recipient_id} via {evidence}")


def handle_inbound(from_phone: str, body: str, sid: str) -> str | None:
    """Process an SMS someone sent to our Twilio number.

    Returns the text to reply with, or None for no reply. STOP/START/HELP replies
    are left to Twilio's built-in opt-out handling so the person never gets two.
    """
    db = get_db()
    ts = now_iso()
    recipient = db.execute("SELECT * FROM recipients WHERE phone = ?", (from_phone,)).fetchone()
    keyword = (body or "").strip().upper().rstrip(".!")

    if recipient is None and keyword in OPT_OUT_WORDS:
        # Unknown number said STOP: remember it so it can never be added and contacted.
        cur = db.execute(
            "INSERT INTO recipients(phone, name, status, opted_out_at, consent_evidence, created_at) "
            "VALUES (?, '', 'opted_out', ?, ?, ?)", (from_phone, ts, f"sms:{sid}", ts))
        recipient = db.execute("SELECT * FROM recipients WHERE id = ?", (cur.lastrowid,)).fetchone()

    db.execute(
        "INSERT OR IGNORE INTO messages(recipient_id, phone, direction, kind, body, twilio_sid, status, created_at, updated_at) "
        "VALUES (?, ?, 'inbound', 'inbound', ?, ?, 'received', ?, ?)",
        (recipient["id"] if recipient else None, from_phone, (body or "")[:1600], sid, ts, ts),
    )
    if recipient is None:
        return None

    if keyword in OPT_OUT_WORDS:
        _mark_opted_out(recipient["id"], f"sms:{sid}")
        return None
    if keyword in OPT_IN_WORDS:
        was_consented = recipient["status"] == "consented"
        _mark_consented(recipient["id"], f"sms:{sid}")
        # Twilio auto-replies to START/UNSTOP itself; we confirm YES / Y.
        if keyword in {"YES", "Y"} and not was_consented:
            return sms.optin_confirmed_text(settings())
    return None


def apply_status_update(sid: str, status: str, error_code: str | None, error_message: str | None) -> bool:
    db = get_db()
    row = db.execute("SELECT id, status FROM messages WHERE twilio_sid = ?", (sid,)).fetchone()
    if row is None:
        return False
    # Callbacks can arrive out of order; never move backwards (e.g. delivered -> sent).
    current = row["status"]
    if current in sms.FINAL_STATUSES and status not in sms.FINAL_STATUSES:
        return True
    if current in sms.STATUS_ORDER and status in sms.STATUS_ORDER and \
            sms.STATUS_ORDER.index(status) < sms.STATUS_ORDER.index(current):
        return True
    db.execute(
        "UPDATE messages SET status = ?, error_code = COALESCE(?, error_code), "
        "error_message = COALESCE(?, error_message), updated_at = ? WHERE id = ?",
        (status, error_code, error_message, now_iso(), row["id"]),
    )
    if error_code == "21610":
        rec = db.execute("SELECT recipient_id FROM messages WHERE id = ?", (row["id"],)).fetchone()
        if rec and rec["recipient_id"]:
            _mark_opted_out(rec["recipient_id"], "twilio:21610")
    return True


def stats() -> dict:
    db = get_db()
    s = settings()
    day = start_of_local_day_utc()
    row = db.execute(
        "SELECT "
        " SUM(CASE WHEN status NOT IN ('failed') THEN 1 ELSE 0 END) AS sent,"
        " SUM(CASE WHEN status IN ('delivered','read') THEN 1 ELSE 0 END) AS delivered,"
        " SUM(CASE WHEN status IN ('failed','undelivered') THEN 1 ELSE 0 END) AS failed,"
        " SUM(CASE WHEN status NOT IN ('delivered','read','failed','undelivered','canceled') THEN 1 ELSE 0 END) AS pending"
        " FROM messages WHERE direction = 'outbound' AND created_at >= ?", (day,),
    ).fetchone()
    rec = db.execute(
        "SELECT SUM(status='consented' AND paused=0) AS active, SUM(status='pending') AS pending,"
        " SUM(status='opted_out') AS opted_out FROM recipients"
    ).fetchone()
    return {
        "sending_enabled": sending_enabled(),
        "sent_today": row["sent"] or 0,
        "delivered_today": row["delivered"] or 0,
        "failed_today": row["failed"] or 0,
        "in_flight_today": row["pending"] or 0,
        "daily_limit": s.global_daily_limit,
        "recipients_active": rec["active"] or 0,
        "recipients_pending": rec["pending"] or 0,
        "recipients_opted_out": rec["opted_out"] or 0,
    }
