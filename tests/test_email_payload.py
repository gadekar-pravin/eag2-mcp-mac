"""Tests for the reusable email payload helpers."""
from __future__ import annotations

from client.email_payload import (
    DEFAULT_SUBJECT,
    build_log_email_payload,
)


def test_build_log_email_payload_with_entries(tmp_path):
    log_path = tmp_path / "agent.log"
    log_lines = [
        "[2024-05-01T10:00:00.000Z][client][run_id=abcd1234] iteration=1 user_message=Hello",
        "[2024-05-01T10:00:00.100Z][server][tool=send_email] EMAIL_SENT: to=demo@example.com, id=123",
    ]
    log_path.write_text("\n".join(log_lines), encoding="utf-8")

    payload = build_log_email_payload(log_path=log_path)

    assert payload["subject"] == DEFAULT_SUBJECT
    body = payload["body"]
    assert "Agent Log Transcript" in body
    assert "- 2024-05-01T10:00:00.000Z | client | run_id=abcd1234 -> iteration=1 user_message=Hello" in body
    assert "EMAIL_SENT" in body

    html = payload.get("body_html")
    assert html is not None
    assert "<table" in html
    assert "demo@example.com" in html


def test_build_log_email_payload_missing_log(tmp_path):
    missing_log = tmp_path / "missing.log"

    payload = build_log_email_payload(log_path=missing_log)

    assert payload["subject"] == DEFAULT_SUBJECT
    assert payload["body"] == "Agent log not found."
    assert "Agent log not found." in payload.get("body_html", "")
