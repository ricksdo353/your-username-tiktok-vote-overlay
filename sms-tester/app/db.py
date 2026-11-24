"""SQLite storage. One file, no extra server needed."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS recipients (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    phone                 TEXT NOT NULL UNIQUE,
    name                  TEXT NOT NULL DEFAULT '',
    status                TEXT NOT NULL DEFAULT 'pending'
                          CHECK (status IN ('pending', 'consented', 'opted_out')),
    paused                INTEGER NOT NULL DEFAULT 0,
    attested_at           TEXT,
    optin_requests        INTEGER NOT NULL DEFAULT 0,
    last_optin_request_at TEXT,
    consent_confirmed_at  TEXT,
    consent_evidence      TEXT,
    opted_out_at          TEXT,
    created_at            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS templates (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_id  INTEGER REFERENCES recipients(id) ON DELETE SET NULL,
    phone         TEXT NOT NULL,
    direction     TEXT NOT NULL CHECK (direction IN ('outbound', 'inbound')),
    kind          TEXT NOT NULL CHECK (kind IN ('test', 'optin', 'reply', 'inbound')),
    body          TEXT NOT NULL,
    twilio_sid    TEXT UNIQUE,
    status        TEXT NOT NULL,
    error_code    TEXT,
    error_message TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id, created_at);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id  INTEGER PRIMARY KEY AUTOINCREMENT,
    ip  TEXT NOT NULL,
    ts  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_login_attempts ON login_attempts(ip, ts);

CREATE TABLE IF NOT EXISTS audit_log (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts     TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT ''
);
"""

DEFAULT_TEMPLATES = [
    ("Basic test", "Hi {first_name}, this is a test message from {app_name} sent {date} at {time}."),
    ("Delivery check", "Delivery check #{date}-{time}. No reply needed, {first_name}."),
    ("Reminder", "Hi {first_name}, friendly reminder from {app_name}: your test is scheduled for today."),
]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_iso() -> str:
    return iso(utcnow())


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=15, isolation_level=None)  # autocommit; explicit BEGIN when needed
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES ('sending_enabled', '1')")
        if conn.execute("SELECT COUNT(*) FROM templates").fetchone()[0] == 0:
            ts = now_iso()
            conn.executemany(
                "INSERT INTO templates(name, body, created_at, updated_at) VALUES (?, ?, ?, ?)",
                [(n, b, ts, ts) for n, b in DEFAULT_TEMPLATES],
            )
    finally:
        conn.close()


def get_setting(key: str, default: str = "") -> str:
    row = get_db().execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    get_db().execute(
        "INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def audit(action: str, detail: str = "") -> None:
    get_db().execute(
        "INSERT INTO audit_log(ts, action, detail) VALUES (?, ?, ?)", (now_iso(), action, detail[:500])
    )
