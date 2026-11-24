"""All configuration comes from environment variables.

Secrets (Twilio credentials, admin password, secret key) are read here on the
server only. Nothing in this module is ever sent to the browser except the
non-secret values that `public_summary()` deliberately exposes.
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_int(name: str, default: int, minimum: int = 0, maximum: int = 10_000) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a whole number, got {raw!r}") from exc
    if not minimum <= value <= maximum:
        raise ConfigError(f"{name} must be between {minimum} and {maximum}, got {value}")
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name).lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{name} must be true or false, got {raw!r}")


class ConfigError(RuntimeError):
    """Raised at startup when the environment is misconfigured."""


@dataclass
class Settings:
    # Core
    app_name: str
    secret_key: str
    admin_password: str
    database_path: str
    public_base_url: str
    timezone: ZoneInfo
    cookie_secure: bool

    # Twilio
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from_number: str
    twilio_messaging_service_sid: str
    sms_mode: str  # "live" or "dry_run"

    # Safety limits
    global_daily_limit: int
    global_per_minute_limit: int
    recipient_daily_limit: int
    recipient_min_interval_seconds: int
    duplicate_window_minutes: int
    max_body_chars: int
    optin_cooldown_hours: int
    optin_max_requests: int
    append_opt_out_footer: bool
    default_country_code: str

    warnings: list[str] = field(default_factory=list)

    @property
    def is_live(self) -> bool:
        return self.sms_mode == "live"

    def masked_sid(self) -> str:
        sid = self.twilio_account_sid
        return f"{sid[:2]}…{sid[-4:]}" if len(sid) > 8 else ("set" if sid else "not set")

    def sender_label(self) -> str:
        if self.twilio_messaging_service_sid:
            s = self.twilio_messaging_service_sid
            return f"Messaging Service {s[:2]}…{s[-4:]}"
        return self.twilio_from_number or "not set"


def load_settings() -> Settings:
    warnings: list[str] = []

    secret_key = _env("SECRET_KEY")
    if not secret_key:
        # A random key works but logs everyone out on every restart.
        secret_key = secrets.token_hex(32)
        warnings.append("SECRET_KEY is not set; using a temporary key (you will be logged out on restart).")
    elif len(secret_key) < 32:
        raise ConfigError("SECRET_KEY must be at least 32 characters long.")

    admin_password = _env("ADMIN_PASSWORD")
    if not admin_password:
        raise ConfigError("ADMIN_PASSWORD is not set. Choose a password of at least 12 characters.")
    if len(admin_password) < 12:
        raise ConfigError("ADMIN_PASSWORD must be at least 12 characters long.")

    tz_name = _env("APP_TIMEZONE", "UTC")
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ConfigError(f"APP_TIMEZONE {tz_name!r} is not a valid time zone (example: America/New_York).") from exc

    sid = _env("TWILIO_ACCOUNT_SID")
    token = _env("TWILIO_AUTH_TOKEN")
    from_number = _env("TWILIO_FROM_NUMBER")
    msid = _env("TWILIO_MESSAGING_SERVICE_SID")

    if sid and not sid.startswith("AC"):
        raise ConfigError("TWILIO_ACCOUNT_SID should start with 'AC'.")
    if msid and not msid.startswith("MG"):
        raise ConfigError("TWILIO_MESSAGING_SERVICE_SID should start with 'MG'.")
    if from_number and not from_number.startswith("+"):
        raise ConfigError("TWILIO_FROM_NUMBER must be in +E.164 format, e.g. +15551234567.")

    have_creds = bool(sid and token and (from_number or msid))
    mode = _env("SMS_MODE", "live" if have_creds else "dry_run").lower()
    if mode not in {"live", "dry_run"}:
        raise ConfigError("SMS_MODE must be 'live' or 'dry_run'.")
    if mode == "live" and not have_creds:
        raise ConfigError(
            "SMS_MODE is live but Twilio is not fully configured. Set TWILIO_ACCOUNT_SID, "
            "TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER (or TWILIO_MESSAGING_SERVICE_SID)."
        )
    if mode == "dry_run":
        warnings.append("Dry-run mode: no real SMS is sent. Add Twilio credentials to go live.")

    public_base_url = _env("PUBLIC_BASE_URL").rstrip("/")
    if public_base_url and not public_base_url.startswith(("https://", "http://")):
        raise ConfigError("PUBLIC_BASE_URL must start with https:// (e.g. https://my-sms-app.onrender.com).")
    if mode == "live" and not public_base_url:
        warnings.append("PUBLIC_BASE_URL is not set, so Twilio cannot push delivery updates. Use 'Refresh statuses' instead.")

    return Settings(
        app_name=_env("APP_NAME", "SMS Tester")[:40],
        secret_key=secret_key,
        admin_password=admin_password,
        database_path=_env("DATABASE_PATH", os.path.join(os.getcwd(), "instance", "sms_tester.db")),
        public_base_url=public_base_url,
        timezone=tz,
        cookie_secure=_env_bool("COOKIE_SECURE", True),
        twilio_account_sid=sid,
        twilio_auth_token=token,
        twilio_from_number=from_number,
        twilio_messaging_service_sid=msid,
        sms_mode=mode,
        global_daily_limit=_env_int("GLOBAL_DAILY_LIMIT", 50, 1, 1000),
        global_per_minute_limit=_env_int("GLOBAL_PER_MINUTE_LIMIT", 5, 1, 60),
        recipient_daily_limit=_env_int("RECIPIENT_DAILY_LIMIT", 5, 1, 100),
        recipient_min_interval_seconds=_env_int("RECIPIENT_MIN_INTERVAL_SECONDS", 60, 10, 86_400),
        duplicate_window_minutes=_env_int("DUPLICATE_WINDOW_MINUTES", 10, 0, 1440),
        max_body_chars=_env_int("MAX_BODY_CHARS", 480, 20, 1600),
        optin_cooldown_hours=_env_int("OPTIN_COOLDOWN_HOURS", 24, 1, 720),
        optin_max_requests=_env_int("OPTIN_MAX_REQUESTS", 2, 1, 5),
        append_opt_out_footer=_env_bool("APPEND_OPT_OUT_FOOTER", True),
        default_country_code=_env("DEFAULT_COUNTRY_CODE").lstrip("+"),
        warnings=warnings,
    )
