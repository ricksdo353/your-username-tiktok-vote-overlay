"""Admin pages and the small JSON API the dashboard polls."""
from __future__ import annotations

import secrets
from datetime import timedelta

from flask import (Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request,
                   url_for)

from . import services, sms
from .auth import login_required
from .db import audit, get_db, iso, now_iso, set_setting, utcnow

bp = Blueprint("main", __name__)

PAGE_SIZE = 25


def _settings():
    return current_app.config["SETTINGS"]


@bp.app_context_processor
def inject_globals():
    s = _settings()
    return {"app_name": s.app_name, "is_live": s.is_live, "mask_phone": sms.mask_phone}


def _message_dict(row) -> dict:
    return {
        "id": row["id"],
        "phone": sms.mask_phone(row["phone"]),
        "name": row["name"] if "name" in row.keys() else "",
        "direction": row["direction"],
        "kind": row["kind"],
        "body": row["body"],
        "status": row["status"],
        "error_code": row["error_code"],
        "error_message": row["error_message"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


MESSAGE_SELECT = (
    "SELECT m.*, COALESCE(r.name, '') AS name FROM messages m LEFT JOIN recipients r ON r.id = m.recipient_id"
)


# ---------------------------------------------------------------- pages

@bp.get("/")
@login_required
def dashboard():
    db = get_db()
    recipients = db.execute(
        "SELECT * FROM recipients WHERE status = 'consented' AND paused = 0 ORDER BY name COLLATE NOCASE"
    ).fetchall()
    templates = db.execute("SELECT * FROM templates ORDER BY name COLLATE NOCASE").fetchall()
    messages = db.execute(f"{MESSAGE_SELECT} ORDER BY m.id DESC LIMIT 15").fetchall()
    return render_template(
        "dashboard.html", stats=services.stats(), recipients=recipients, templates=templates,
        messages=[_message_dict(m) for m in messages], settings=_settings(),
    )


@bp.post("/send")
@login_required
def send():
    try:
        recipient_id = int(request.form.get("recipient_id", "0"))
    except ValueError:
        recipient_id = 0
    body = request.form.get("body", "").strip()
    try:
        services.send_test_message(recipient_id, body)
        flash("Message sent." if _settings().is_live else "Simulated send (dry-run mode).", "success")
    except services.SendBlocked as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.dashboard"))


@bp.post("/sending/<state>")
@login_required
def toggle_sending(state: str):
    if state not in {"start", "stop"}:
        abort(404)
    set_setting("sending_enabled", "1" if state == "start" else "0")
    audit(f"sending_{state}")
    flash("Sending STARTED." if state == "start" else "Sending STOPPED. No messages will go out.",
          "success" if state == "start" else "warning")
    return redirect(request.referrer or url_for("main.dashboard"))


# ----- recipients

@bp.get("/recipients")
@login_required
def recipients():
    rows = get_db().execute(
        "SELECT r.*, (SELECT MAX(created_at) FROM messages WHERE recipient_id = r.id AND direction='outbound') AS last_sent "
        "FROM recipients r ORDER BY CASE status WHEN 'consented' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END, "
        "name COLLATE NOCASE"
    ).fetchall()
    return render_template("recipients.html", recipients=rows, settings=_settings())


@bp.post("/recipients")
@login_required
def add_recipient():
    s = _settings()
    name = request.form.get("name", "").strip()[:60]
    phone = sms.normalize_phone(request.form.get("phone", ""), s.default_country_code)
    if not phone:
        flash("Enter the number in international format, e.g. +1 555 123 4567.", "error")
        return redirect(url_for("main.recipients"))
    if request.form.get("attest") != "yes":
        flash("You must confirm this person agreed to receive a consent request.", "error")
        return redirect(url_for("main.recipients"))
    if s.twilio_from_number and phone == s.twilio_from_number:
        flash("That is your own Twilio number.", "error")
        return redirect(url_for("main.recipients"))
    db = get_db()
    existing = db.execute("SELECT status FROM recipients WHERE phone = ?", (phone,)).fetchone()
    if existing:
        msg = ("This number opted out and cannot be re-added. They can text START to your number to opt back in."
               if existing["status"] == "opted_out" else "That number is already in your list.")
        flash(msg, "error")
        return redirect(url_for("main.recipients"))
    cur = db.execute(
        "INSERT INTO recipients(phone, name, status, attested_at, created_at) VALUES (?, ?, 'pending', ?, ?)",
        (phone, name, now_iso(), now_iso()),
    )
    audit("recipient_add", f"recipient #{cur.lastrowid}")
    flash("Recipient added. Next: send them a consent request — they must reply YES.", "success")
    return redirect(url_for("main.recipients"))


@bp.post("/recipients/<int:rid>/optin")
@login_required
def request_optin(rid: int):
    try:
        services.send_optin_request(rid)
        flash("Consent request sent. They'll appear as Active once they reply YES.", "success")
    except services.SendBlocked as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.recipients"))


@bp.post("/recipients/<int:rid>/pause")
@login_required
def pause_recipient(rid: int):
    paused = 1 if request.form.get("paused") == "1" else 0
    get_db().execute("UPDATE recipients SET paused = ? WHERE id = ?", (paused, rid))
    audit("recipient_pause" if paused else "recipient_resume", f"recipient #{rid}")
    flash("Recipient paused." if paused else "Recipient resumed.", "success")
    return redirect(url_for("main.recipients"))


@bp.post("/recipients/<int:rid>/delete")
@login_required
def delete_recipient(rid: int):
    db = get_db()
    row = db.execute("SELECT status FROM recipients WHERE id = ?", (rid,)).fetchone()
    if row is None:
        abort(404)
    if row["status"] == "opted_out":
        flash("Opted-out numbers are kept on file so they are never contacted again.", "error")
    else:
        db.execute("DELETE FROM recipients WHERE id = ?", (rid,))
        audit("recipient_delete", f"recipient #{rid}")
        flash("Recipient removed.", "success")
    return redirect(url_for("main.recipients"))


@bp.post("/recipients/<int:rid>/simulate")
@login_required
def simulate_reply(rid: int):
    """Dry-run only: pretend the recipient texted a keyword, to try the consent flow without Twilio."""
    if _settings().is_live:
        abort(404)
    word = request.form.get("word", "").upper()
    if word not in {"YES", "STOP", "START"}:
        abort(400)
    row = get_db().execute("SELECT phone FROM recipients WHERE id = ?", (rid,)).fetchone()
    if row is None:
        abort(404)
    services.handle_inbound(row["phone"], word, "SMsim" + secrets.token_hex(14))
    flash(f"Simulated reply “{word}”.", "success")
    return redirect(url_for("main.recipients"))


# ----- templates

@bp.get("/templates")
@login_required
def templates():
    rows = get_db().execute("SELECT * FROM templates ORDER BY name COLLATE NOCASE").fetchall()
    edit_id = request.args.get("edit", type=int)
    editing = next((t for t in rows if t["id"] == edit_id), None)
    return render_template("templates.html", templates=rows, editing=editing, settings=_settings())


@bp.post("/templates")
@login_required
def save_template():
    s = _settings()
    name = request.form.get("name", "").strip()[:60]
    body = request.form.get("body", "").strip()
    tid = request.form.get("id", type=int)
    if not name or not body:
        flash("Template needs a name and text.", "error")
        return redirect(url_for("main.templates", edit=tid) if tid else url_for("main.templates"))
    if len(body) > s.max_body_chars:
        flash(f"Template is too long (max {s.max_body_chars} characters).", "error")
        return redirect(url_for("main.templates"))
    db = get_db()
    if tid:
        db.execute("UPDATE templates SET name = ?, body = ?, updated_at = ? WHERE id = ?", (name, body, now_iso(), tid))
        flash("Template updated.", "success")
    else:
        db.execute("INSERT INTO templates(name, body, created_at, updated_at) VALUES (?, ?, ?, ?)",
                   (name, body, now_iso(), now_iso()))
        flash("Template created.", "success")
    return redirect(url_for("main.templates"))


@bp.post("/templates/<int:tid>/delete")
@login_required
def delete_template(tid: int):
    get_db().execute("DELETE FROM templates WHERE id = ?", (tid,))
    flash("Template deleted.", "success")
    return redirect(url_for("main.templates"))


# ----- history & settings

@bp.get("/history")
@login_required
def history():
    status = request.args.get("status", "")
    page = max(1, request.args.get("page", 1, type=int))
    where, params = [], []
    if status == "delivered":
        where.append("m.status IN ('delivered','read')")
    elif status == "failed":
        where.append("m.status IN ('failed','undelivered')")
    elif status == "pending":
        where.append("m.direction='outbound' AND m.status NOT IN ('delivered','read','failed','undelivered','canceled')")
    elif status == "inbound":
        where.append("m.direction='inbound'")
    clause = f" WHERE {' AND '.join(where)}" if where else ""
    db = get_db()
    total = db.execute(f"SELECT COUNT(*) FROM messages m{clause}", params).fetchone()[0]
    rows = db.execute(f"{MESSAGE_SELECT}{clause} ORDER BY m.id DESC LIMIT ? OFFSET ?",
                      (*params, PAGE_SIZE, (page - 1) * PAGE_SIZE)).fetchall()
    return render_template(
        "history.html", messages=[_message_dict(r) for r in rows], status=status, page=page,
        has_next=page * PAGE_SIZE < total, total=total,
    )


@bp.get("/settings")
@login_required
def settings_page():
    s = _settings()
    base = s.public_base_url or request.host_url.rstrip("/")
    log = get_db().execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 30").fetchall()
    return render_template("settings.html", settings=s, base=base, audit=log, stats=services.stats())


# ---------------------------------------------------------------- JSON API (session-authenticated)

@bp.get("/api/stats")
@login_required
def api_stats():
    return jsonify(services.stats())


@bp.get("/api/messages")
@login_required
def api_messages():
    limit = min(50, max(1, request.args.get("limit", 15, type=int)))
    rows = get_db().execute(f"{MESSAGE_SELECT} ORDER BY m.id DESC LIMIT ?", (limit,)).fetchall()
    return jsonify({"messages": [_message_dict(r) for r in rows], "stats": services.stats()})


@bp.post("/api/messages/sync")
@login_required
def api_sync():
    """Pull the latest status from Twilio for recent messages that are not final yet."""
    rows = get_db().execute(
        "SELECT twilio_sid FROM messages WHERE direction='outbound' AND twilio_sid IS NOT NULL "
        "AND status NOT IN ('delivered','read','failed','undelivered','canceled') AND created_at >= ? "
        "ORDER BY id DESC LIMIT 20",
        (iso(utcnow() - timedelta(days=3)),),
    ).fetchall()
    updated = 0
    for row in rows:
        result = sms.fetch_status(row["twilio_sid"])
        if result and services.apply_status_update(row["twilio_sid"], result.status, result.error_code,
                                                   result.error_message):
            updated += 1
    return jsonify({"checked": len(rows), "updated": updated})
