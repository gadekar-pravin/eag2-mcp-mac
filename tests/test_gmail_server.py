# File: tests/test_gmail_server.py
import base64
import importlib

gmail_mod = importlib.import_module("gmail_bonus.mcp_server_gmail")


class _FakeSendExec:
    def execute(self):
        return {"id": "MSG-12345"}


def test_send_email_success(monkeypatch):
    # Avoid hitting real OAuth/Gmail
    captured = {}

    class _FakeMessages:
        def send(self, userId, body):
            assert userId == "me"
            assert "raw" in body and isinstance(body["raw"], str) and len(body["raw"]) > 10
            captured["raw"] = body["raw"]
            return _FakeSendExec()

    class _FakeUsers:
        def messages(self):
            return _FakeMessages()

    class _FakeService:
        def users(self):
            return _FakeUsers()

    monkeypatch.setattr(gmail_mod, "_build_gmail_service", lambda: _FakeService())
    result = gmail_mod.send_email(
        "to@example.com",
        "Hello",
        "Body",
        body_html="<p><strong>Body</strong></p>",
    )
    assert result.startswith("EMAIL_SENT: to=to@example.com, id=MSG-12345")
    assert "raw" in captured

    decoded = base64.urlsafe_b64decode(captured["raw"]).decode("utf-8")
    assert "multipart/alternative" in decoded
    assert "Content-Type: text/plain" in decoded
    assert "Body" in decoded
    assert "Content-Type: text/html" in decoded
    assert "<strong>Body</strong>" in decoded


def test_send_email_input_validation():
    # No monkeypatch needed; it should fail fast on address check
    result = gmail_mod.send_email("not-an-email", "S", "B")
    assert result.startswith('ERROR: Invalid "to" address.')
