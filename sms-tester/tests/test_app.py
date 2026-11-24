"""End-to-end tests in dry-run mode (no real SMS, no network)."""
import re
from unittest import mock

import pytest
from twilio.request_validator import RequestValidator

PASSWORD = "correct-horse-battery"
TOKEN = "test_auth_token_0123456789abcdef"
BASE = "https://sms.example.com"


@pytest.fixture
def app(tmp_path, monkeypatch):
    for key in list(__import__("os").environ):
        if key.startswith("TWILIO_") or key in {"SMS_MODE", "PUBLIC_BASE_URL"}:
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("SMS_MODE", "dry_run")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)  # only used to validate webhook signatures
    monkeypatch.setenv("PUBLIC_BASE_URL", BASE)
    monkeypatch.setenv("RECIPIENT_MIN_INTERVAL_SECONDS", "10")
    monkeypatch.setenv("RECIPIENT_DAILY_LIMIT", "3")
    from app import create_app

    return create_app()


@pytest.fixture
def client(app):
    return app.test_client()


def csrf(client, path="/"):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)


def login(client):
    token = csrf(client, "/login")
    r = client.post("/login", data={"password": PASSWORD, "csrf_token": token})
    assert r.status_code == 302
    return csrf(client)


def add_and_consent(client, token, phone="+15005550006", name="Alex"):
    client.post("/recipients", data={"name": name, "phone": phone, "attest": "yes", "csrf_token": token})
    from app.db import connect
    db = connect(client.application.config["DATABASE_PATH"])
    rid = db.execute("SELECT id FROM recipients WHERE phone = ?", (phone,)).fetchone()[0]
    client.post(f"/recipients/{rid}/optin", data={"csrf_token": token})
    client.post(f"/recipients/{rid}/simulate", data={"word": "YES", "csrf_token": token})
    return rid, db


def signed_post(client, path, form):
    sig = RequestValidator(TOKEN).compute_signature(BASE + path, form)
    return client.post(path, data=form, headers={"X-Twilio-Signature": sig})


def test_requires_login(client):
    assert client.get("/").status_code == 302
    assert client.get("/api/messages").status_code == 401


def test_wrong_password_and_lockout(client):
    token = csrf(client, "/login")
    for _ in range(5):
        assert client.post("/login", data={"password": "nope", "csrf_token": token}).status_code == 401
    assert client.post("/login", data={"password": PASSWORD, "csrf_token": token}).status_code == 429


def test_csrf_required(client):
    login(client)
    assert client.post("/sending/stop").status_code == 400


def test_no_secrets_in_pages(client):
    login(client)
    for page in ["/", "/recipients", "/templates", "/history", "/settings"]:
        html = client.get(page).get_data(as_text=True)
        assert TOKEN not in html and PASSWORD not in html


def test_consent_flow_and_send(client):
    token = login(client)
    client.post("/recipients", data={"name": "Sam", "phone": "+1 (500) 555-0006", "attest": "yes", "csrf_token": token})
    from app.db import connect
    db = connect(client.application.config["DATABASE_PATH"])
    rid = db.execute("SELECT id FROM recipients").fetchone()[0]

    # Not consented yet -> blocked
    client.post("/send", data={"recipient_id": rid, "body": "hello", "csrf_token": token})
    assert db.execute("SELECT COUNT(*) FROM messages WHERE kind='test'").fetchone()[0] == 0

    client.post(f"/recipients/{rid}/optin", data={"csrf_token": token})
    # Second consent request within cooldown is refused
    client.post(f"/recipients/{rid}/optin", data={"csrf_token": token})
    assert db.execute("SELECT COUNT(*) FROM messages WHERE kind='optin'").fetchone()[0] == 1

    client.post(f"/recipients/{rid}/simulate", data={"word": "YES", "csrf_token": token})
    assert db.execute("SELECT status FROM recipients").fetchone()[0] == "consented"

    r = client.post("/send", data={"recipient_id": rid, "body": "Hi {first_name}", "csrf_token": token}, follow_redirects=True)
    assert "Simulated send" in r.get_data(as_text=True)
    body = db.execute("SELECT body FROM messages WHERE kind='test'").fetchone()[0]
    assert body.startswith("Hi Sam") and "Reply STOP to opt out." in body


def test_rate_limits(client):
    token = login(client)
    rid, db = add_and_consent(client, token)
    client.post("/send", data={"recipient_id": rid, "body": "one", "csrf_token": token})
    r = client.post("/send", data={"recipient_id": rid, "body": "two", "csrf_token": token}, follow_redirects=True)
    assert "Please wait" in r.get_data(as_text=True)
    assert db.execute("SELECT COUNT(*) FROM messages WHERE kind='test'").fetchone()[0] == 1


def test_duplicate_blocked(client):
    token = login(client)
    rid, db = add_and_consent(client, token)
    client.post("/send", data={"recipient_id": rid, "body": "same", "csrf_token": token})
    # Move the first send past the min-interval so only the duplicate rule applies.
    db.execute("UPDATE messages SET created_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-30 seconds') WHERE kind='test'")
    r = client.post("/send", data={"recipient_id": rid, "body": "same", "csrf_token": token}, follow_redirects=True)
    assert "Same text" in r.get_data(as_text=True)


def test_recipient_daily_limit(client):
    token = login(client)
    rid, db = add_and_consent(client, token)
    for i in range(4):
        db.execute("UPDATE messages SET created_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-30 seconds') WHERE kind='test'")
        r = client.post("/send", data={"recipient_id": rid, "body": f"msg {i}", "csrf_token": token}, follow_redirects=True)
    assert "already got 3 messages today" in r.get_data(as_text=True)
    assert db.execute("SELECT COUNT(*) FROM messages WHERE kind='test'").fetchone()[0] == 3


def test_stop_controls(client):
    token = login(client)
    rid, db = add_and_consent(client, token)
    client.post("/sending/stop", data={"csrf_token": token})
    r = client.post("/send", data={"recipient_id": rid, "body": "hi", "csrf_token": token}, follow_redirects=True)
    assert "STOPPED" in r.get_data(as_text=True)
    client.post("/sending/start", data={"csrf_token": token})
    client.post("/send", data={"recipient_id": rid, "body": "hi", "csrf_token": token})
    assert db.execute("SELECT COUNT(*) FROM messages WHERE kind='test'").fetchone()[0] == 1


def test_paused_recipient_blocked(client):
    token = login(client)
    rid, db = add_and_consent(client, token)
    client.post(f"/recipients/{rid}/pause", data={"paused": "1", "csrf_token": token})
    client.post("/send", data={"recipient_id": rid, "body": "hi", "csrf_token": token})
    assert db.execute("SELECT COUNT(*) FROM messages WHERE kind='test'").fetchone()[0] == 0


def test_inbound_webhook_requires_signature(client):
    form = {"From": "+15005550006", "Body": "STOP", "MessageSid": "SM" + "a" * 32}
    assert client.post("/twilio/inbound", data=form).status_code == 403
    assert client.post("/twilio/inbound", data=form, headers={"X-Twilio-Signature": "bad"}).status_code == 403


def test_inbound_stop_and_start(client):
    token = login(client)
    rid, db = add_and_consent(client, token)
    r = signed_post(client, "/twilio/inbound", {"From": "+15005550006", "Body": " stop ", "MessageSid": "SM" + "b" * 32})
    assert r.status_code == 200 and "<Message>" not in r.get_data(as_text=True)
    assert db.execute("SELECT status FROM recipients WHERE id=?", (rid,)).fetchone()[0] == "opted_out"
    # Opted-out numbers can't be deleted or re-added
    client.post(f"/recipients/{rid}/delete", data={"csrf_token": token})
    assert db.execute("SELECT COUNT(*) FROM recipients").fetchone()[0] == 1
    client.post("/send", data={"recipient_id": rid, "body": "hi", "csrf_token": token})
    assert db.execute("SELECT COUNT(*) FROM messages WHERE kind='test'").fetchone()[0] == 0
    signed_post(client, "/twilio/inbound", {"From": "+15005550006", "Body": "START", "MessageSid": "SM" + "c" * 32})
    assert db.execute("SELECT status FROM recipients WHERE id=?", (rid,)).fetchone()[0] == "consented"


def test_unknown_number_stop_is_suppressed(client):
    token = login(client)
    signed_post(client, "/twilio/inbound", {"From": "+15005550009", "Body": "STOP", "MessageSid": "SM" + "d" * 32})
    r = client.post("/recipients", data={"phone": "+15005550009", "attest": "yes", "csrf_token": token}, follow_redirects=True)
    assert "opted out" in r.get_data(as_text=True)


def test_yes_reply_confirms(client):
    token = login(client)
    client.post("/recipients", data={"name": "Kim", "phone": "+15005550007", "attest": "yes", "csrf_token": token})
    r = signed_post(client, "/twilio/inbound", {"From": "+15005550007", "Body": "Yes", "MessageSid": "SM" + "e" * 32})
    assert "confirmed" in r.get_data(as_text=True)


def test_status_callback(client):
    token = login(client)
    rid, db = add_and_consent(client, token)
    client.post("/send", data={"recipient_id": rid, "body": "hi", "csrf_token": token})
    sid = db.execute("SELECT twilio_sid FROM messages WHERE kind='test'").fetchone()[0]
    db.execute("UPDATE messages SET status='sent' WHERE twilio_sid=?", (sid,))
    assert signed_post(client, "/twilio/status", {"MessageSid": sid, "MessageStatus": "undelivered", "ErrorCode": "30003"}).status_code == 204
    row = db.execute("SELECT status, error_code FROM messages WHERE twilio_sid=?", (sid,)).fetchone()
    assert tuple(row) == ("undelivered", "30003")
    # Out-of-order "sent" must not overwrite a final status
    signed_post(client, "/twilio/status", {"MessageSid": sid, "MessageStatus": "sent"})
    assert db.execute("SELECT status FROM messages WHERE twilio_sid=?", (sid,)).fetchone()[0] == "undelivered"


def test_live_send_uses_twilio_client(app, client, monkeypatch):
    s = app.config["SETTINGS"]
    monkeypatch.setattr(s, "sms_mode", "live")
    monkeypatch.setattr(s, "twilio_account_sid", "AC" + "0" * 32)
    monkeypatch.setattr(s, "twilio_from_number", "+15005550000")
    token = login(client)
    client.post("/recipients", data={"name": "Lee", "phone": "+15005550006", "attest": "yes", "csrf_token": token})
    from app.db import connect
    db = connect(app.config["DATABASE_PATH"])
    rid = db.execute("SELECT id FROM recipients").fetchone()[0]
    db.execute("UPDATE recipients SET status='consented' WHERE id=?", (rid,))
    fake = mock.MagicMock()
    fake.messages.create.return_value = mock.Mock(sid="SM" + "f" * 32, status="queued")
    with mock.patch("app.sms._client", return_value=fake):
        client.post("/send", data={"recipient_id": rid, "body": "live test", "csrf_token": token})
    kwargs = fake.messages.create.call_args.kwargs
    assert kwargs["to"] == "+15005550006" and kwargs["from_"] == "+15005550000"
    assert kwargs["status_callback"] == BASE + "/twilio/status"
    assert db.execute("SELECT status FROM messages WHERE kind='test'").fetchone()[0] == "queued"


def test_phone_normalization():
    from app.sms import normalize_phone
    assert normalize_phone("+44 7700 900123") == "+447700900123"
    assert normalize_phone("(555) 123-4567", "1") == "+15551234567"
    assert normalize_phone("12345") is None
    assert normalize_phone("hello") is None
