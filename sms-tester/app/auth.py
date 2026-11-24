"""Admin login, brute-force protection and CSRF tokens."""
from __future__ import annotations

import hmac
import secrets
from datetime import timedelta
from functools import wraps

from flask import (Blueprint, abort, current_app, flash, redirect, render_template, request,
                   session, url_for)

from .db import audit, get_db, iso, now_iso, utcnow

bp = Blueprint("auth", __name__)

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            if request.path.startswith("/api/"):
                return {"error": "Not logged in"}, 401
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapper


def csrf_token() -> str:
    token = session.get("csrf")
    if not token:
        token = session["csrf"] = secrets.token_urlsafe(32)
    return token


def init_csrf(app) -> None:
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def check_csrf():
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return
        if request.blueprint == "webhooks":
            return  # Twilio webhooks are protected by signature validation instead
        sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
        expected = session.get("csrf", "")
        if not expected or not hmac.compare_digest(sent, expected):
            abort(400, description="Your session expired. Reload the page and try again.")


def _client_ip() -> str:
    return request.remote_addr or "unknown"


def _recent_failures(ip: str) -> int:
    since = iso(utcnow() - timedelta(minutes=LOCKOUT_MINUTES))
    db = get_db()
    db.execute("DELETE FROM login_attempts WHERE ts < ?", (iso(utcnow() - timedelta(days=1)),))
    return db.execute("SELECT COUNT(*) FROM login_attempts WHERE ip = ? AND ts >= ?", (ip, since)).fetchone()[0]


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin"):
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        ip = _client_ip()
        if _recent_failures(ip) >= MAX_FAILED_LOGINS:
            flash(f"Too many failed attempts. Try again in {LOCKOUT_MINUTES} minutes.", "error")
            return render_template("login.html"), 429
        password = request.form.get("password", "")
        expected = current_app.config["SETTINGS"].admin_password
        if hmac.compare_digest(password.encode(), expected.encode()):
            session.clear()
            session.permanent = True
            session["admin"] = True
            csrf_token()
            audit("login", ip)
            nxt = request.args.get("next", "")
            # Only allow same-site relative redirects.
            if not nxt.startswith("/") or nxt.startswith("//"):
                nxt = url_for("main.dashboard")
            return redirect(nxt)
        get_db().execute("INSERT INTO login_attempts(ip, ts) VALUES (?, ?)", (ip, now_iso()))
        audit("login_failed", ip)
        flash("Wrong password.", "error")
        return render_template("login.html"), 401
    return render_template("login.html")


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
