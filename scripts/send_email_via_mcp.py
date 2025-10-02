import asyncio
from html import escape
from pathlib import Path
from typing import List, Sequence, Tuple

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "agent.log"

LogEntry = Tuple[str, Tuple[str, ...], str]


def parse_log_line(raw_line: str) -> LogEntry | None:
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
    if not log_path.exists():
        return ()

    entries: List[LogEntry] = []
    for raw_line in log_path.read_text(encoding="utf-8").splitlines():
        parsed = parse_log_line(raw_line)
        if parsed:
            entries.append(parsed)
    return entries


def build_plain_text(entries: Sequence[LogEntry], missing_reason: str | None) -> str:
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


def build_email_content(log_path: Path) -> tuple[str, str]:
    if not log_path.exists():
        reason = "Agent log not found."
        return reason, build_html((), reason)

    entries = load_log_entries(log_path)
    plain_text = build_plain_text(entries, None)
    html = build_html(entries, None)
    return plain_text, html


async def main():
    params = StdioServerParameters(
        command="python",
        args=["-u", "src/gmail_bonus/mcp_server_gmail.py"],
    )
    async with stdio_client(params) as (rs, ws):
        async with ClientSession(read_stream=rs, write_stream=ws) as session:
            await session.initialize()
            text_body, html_body = build_email_content(LOG_PATH)
            payload = {
                "to": "pbgadekar@gmail.com",
                "subject": "MCP Hello - EAG V2 Assignment 4",
                "body": text_body,
            }
            if html_body:
                payload["body_html"] = html_body
            resp = await session.call_tool(
                "send_email",
                payload,
            )
            # The FastMCP client returns an object with .content; print text parts
            out = []
            for c in getattr(resp, "content", []):
                if getattr(c, "type", "") == "text":
                    out.append(c.text)
            print("\n".join(out) if out else str(resp))


if __name__ == "__main__":
    asyncio.run(main())
