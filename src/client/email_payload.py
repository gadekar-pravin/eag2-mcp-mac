"""Utilities for building Gmail email payloads from agent logs."""
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import List, Sequence, Tuple

# Shared location for the agent log used by both the client and helper scripts.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = PROJECT_ROOT / "logs" / "agent.log"

DEFAULT_TO = "pbgadekar@gmail.com"
DEFAULT_SUBJECT = "MCP Hello - EAG V2 Assignment 4"

LogEntry = Tuple[str, Tuple[str, ...], str]


def parse_log_line(raw_line: str) -> LogEntry | None:
    """Return a parsed log entry tuple or ``None`` for empty/invalid lines."""

    stripped = raw_line.strip()
    if not stripped:
        return None

    segments: List[str] = []
    remainder = stripped
    while remainder.startswith("["):
        end = remainder.find("]")
        if end == -1:
            break
        segments.append(remainder[1:end])
        remainder = remainder[end + 1 :].lstrip()

    if not segments and not remainder:
        return None

    timestamp = segments[0] if segments else ""
    metadata = tuple(segments[1:])
    message = remainder
    return timestamp, metadata, message


def load_log_entries(log_path: Path) -> Sequence[LogEntry]:
    """Load structured log entries from ``log_path`` if it exists."""

    if not log_path.exists():
        return ()

    entries: List[LogEntry] = []
    for raw_line in log_path.read_text(encoding="utf-8").splitlines():
        parsed = parse_log_line(raw_line)
        if parsed:
            entries.append(parsed)
    return entries


def build_plain_text(entries: Sequence[LogEntry], missing_reason: str | None) -> str:
    """Create the plaintext email body, handling missing logs gracefully."""

    if missing_reason:
        return missing_reason

    if not entries:
        return "Agent log is empty."

    lines = ["Agent Log Transcript", ""]
    for timestamp, metadata, message in entries:
        meta_text = f" | {' | '.join(metadata)}" if metadata else ""
        msg_text = f" -> {message}" if message else ""
        label = timestamp or "(no timestamp)"
        lines.append(f"- {label}{meta_text}{msg_text}".rstrip())
    return "\n".join(lines)


def build_html(entries: Sequence[LogEntry], missing_reason: str | None) -> str:
    """Create the HTML email body mirroring the plaintext structure."""

    if missing_reason:
        safe = escape(missing_reason)
        return (
            "<!DOCTYPE html>"
            "<html><head><meta charset=\"utf-8\">"
            "<style>body{font-family:Arial,Helvetica,sans-serif;background:#f9fafb;color:#111827;padding:24px;}"
            "h1{font-size:20px;margin-bottom:16px;}"
            "p{font-size:14px;margin:0;}"
            "</style></head><body>"
            f"<h1>Agent Log Transcript</h1><p>{safe}</p></body></html>"
        )

    if not entries:
        return (
            "<!DOCTYPE html>"
            "<html><head><meta charset=\"utf-8\">"
            "<style>body{font-family:Arial,Helvetica,sans-serif;background:#f9fafb;color:#111827;padding:24px;}"
            "h1{font-size:20px;margin-bottom:16px;}"
            "p{font-size:14px;margin:0;}"
            "</style></head><body>"
            "<h1>Agent Log Transcript</h1><p>Agent log is empty.</p></body></html>"
        )

    rows = []
    for timestamp, metadata, message in entries:
        ts_html = escape(timestamp or "—")
        context_parts = "<br>".join(escape(part) for part in metadata) or "&mdash;"
        message_html = escape(message) or "&mdash;"
        rows.append(
            "<tr>"
            f"<td class=\"timestamp\">{ts_html}</td>"
            f"<td class=\"context\">{context_parts}</td>"
            f"<td class=\"message\">{message_html}</td>"
            "</tr>"
        )

    css = (
        "body{font-family:Arial,Helvetica,sans-serif;background:#f9fafb;color:#111827;padding:24px;}"
        "h1{font-size:20px;margin-bottom:16px;}"
        ".log-table{width:100%;border-collapse:collapse;background:#fff;box-shadow:0 10px 30px rgba(15,23,42,0.08);}" 
        ".log-table th{background:#1f2937;color:#f9fafb;text-align:left;padding:12px 16px;font-size:13px;letter-spacing:0.05em;text-transform:uppercase;}"
        ".log-table td{padding:12px 16px;vertical-align:top;border-bottom:1px solid #e5e7eb;font-size:13px;}"
        ".log-table tr:nth-child(even){background:#f3f4f6;}"
        ".timestamp{white-space:nowrap;font-weight:600;}"
        ".context{color:#1d4ed8;}"
        ".message{white-space:pre-wrap;font-family:'SFMono-Regular','Consolas','Liberation Mono',monospace;}"
    )

    return (
        "<!DOCTYPE html>"
        "<html><head><meta charset=\"utf-8\">"
        f"<style>{css}</style>"
        "</head><body>"
        "<h1>Agent Log Transcript</h1>"
        "<table class=\"log-table\">"
        "<thead><tr><th>Timestamp</th><th>Context</th><th>Message</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</body></html>"
    )


def build_email_content(log_path: Path | None = None) -> tuple[str, str]:
    """Return ``(plain_text, html)`` bodies derived from ``log_path``."""

    target = log_path or LOG_PATH
    if not target.exists():
        reason = "Agent log not found."
        return reason, build_html((), reason)

    entries = load_log_entries(target)
    plain_text = build_plain_text(entries, None)
    html = build_html(entries, None)
    return plain_text, html


def build_log_email_payload(
    to: str = DEFAULT_TO,
    subject: str = DEFAULT_SUBJECT,
    log_path: Path | None = None,
) -> dict[str, str]:
    """Create the payload dictionary expected by the Gmail MCP tool."""

    plain_text, html = build_email_content(log_path)
    payload = {
        "to": to,
        "subject": subject,
        "body": plain_text,
    }
    if html:
        payload["body_html"] = html
    return payload


__all__ = [
    "LOG_PATH",
    "DEFAULT_TO",
    "DEFAULT_SUBJECT",
    "LogEntry",
    "parse_log_line",
    "load_log_entries",
    "build_plain_text",
    "build_html",
    "build_email_content",
    "build_log_email_payload",
]
