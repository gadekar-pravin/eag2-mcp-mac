# File: tests/test_gmail_server.py
import importlib
import types

gmail_mod = importlib.import_module("gmail_bonus.mcp_server_gmail")


class _FakeSendExec:
    def execute(self):
        return {"id": "MSG-12345"}


class _FakeMessages:
    def send(self, userId, body):
        assert userId == "me"
        assert "raw" in body and isinstance(body["raw"], str) and len(body["raw"]) > 10
        return _FakeSendExec()


class _FakeUsers:
    def messages(self):
        return _FakeMessages()


class _FakeService:
    def users(self):
        return _FakeUsers()


def test_send_email_success(monkeypatch):
    # Avoid hitting real OAuth/Gmail
    monkeypatch.setattr(gmail_mod, "_build_gmail_service", lambda: _FakeService())
    result = gmail_mod.send_email("to@example.com", "Hello", "Body")
    assert result.startswith("EMAIL_SENT: to=to@example.com, id=MSG-12345")


def test_send_email_input_validation():
    # No monkeypatch needed; it should fail fast on address check
    result = gmail_mod.send_email("not-an-email", "S", "B")
    assert result.startswith('ERROR: Invalid "to" address.')
