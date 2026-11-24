"""Flask application factory."""
from __future__ import annotations

import logging
from datetime import timedelta

from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix

from . import db
from .config import load_settings


def create_app(overrides: dict | None = None) -> Flask:
    settings = load_settings()

    app = Flask(__name__, instance_relative_config=False)
    app.config.update(
        SETTINGS=settings,
        SECRET_KEY=settings.secret_key,
        DATABASE_PATH=settings.database_path,
        SESSION_COOKIE_NAME="smstester_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=settings.cookie_secure,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        MAX_CONTENT_LENGTH=64 * 1024,
        JSON_SORT_KEYS=False,
    )
    if overrides:
        app.config.update(overrides)

    # Hosting platforms (Render, Railway, PythonAnywhere…) sit behind one proxy.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for warning in settings.warnings:
        app.logger.warning(warning)

    db.init_db(app.config["DATABASE_PATH"])
    app.teardown_appcontext(db.close_db)

    from .auth import bp as auth_bp, init_csrf
    from .routes import bp as main_bp
    from .webhooks import bp as webhooks_bp

    init_csrf(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(webhooks_bp)

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'",
        )
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.is_secure:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.path.startswith(("/api/", "/twilio/")) or resp.mimetype == "text/html":
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    from flask import render_template
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(HTTPException)
    def http_error(exc: HTTPException):
        if request.path.startswith(("/api/", "/twilio/")):
            return {"error": exc.description}, exc.code
        return render_template("error.html", code=exc.code, message=exc.description), exc.code

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app
