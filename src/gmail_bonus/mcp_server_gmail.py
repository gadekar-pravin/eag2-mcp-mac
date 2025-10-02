# File: src/gmail_bonus/mcp_server_gmail.py
"""FastMCP server exposing a Gmail send_email tool (OAuth desktop flow)."""
from __future__ import annotations

import base64
import logging
import os
import sys
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("GmailMCP")

# ---- Logging setup ----------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_logger = logging.getLogger("gmail_mcp_server")
if not _logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)sZ][server][%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
_logger.setLevel(LOG_LEVEL)

# ---- Paths & constants ------------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_path(var_name: str, fallback_filename: str) -> Path:
    p = os.getenv(var_name)
    return Path(p).expanduser().resolve() if p else (PROJECT_ROOT / fallback_filename)


def _log_tool(name: str, params: Dict[str, Any], result: str) -> None:
    _logger.info("tool=%s %s", name, {"params": params, "result": result})


# ---- Gmail helpers ----------------------------------------------------------
def _build_gmail_service():
    """Build and return an authorized Gmail API client.

    Uses ~/.env or defaults inside the repo root:
      - GMAIL_CREDENTIALS_PATH (default: ./gmail_credentials.json)
      - GMAIL_TOKEN_PATH (default: ./gmail_token.json)
    """
    # Local imports avoid hard dependency at module import time during tests
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    credentials_path = _env_path("GMAIL_CREDENTIALS_PATH", "gmail_credentials.json")
    token_path = _env_path("GMAIL_TOKEN_PATH", "gmail_token.json")

    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Gmail OAuth client file not found at {credentials_path}. "
            "Download it from Google Cloud Console (OAuth 2.0 Client ID, Desktop app)."
        )

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.refresh_token:
            _logger.info("Refreshing Gmail token...")
            creds.refresh(Request())
        else:
            _logger.info("Starting Gmail OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            # Runs a temporary local server and opens a browser
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        _logger.info("Saved Gmail token to %s", token_path)

    service = build("gmail", "v1", credentials=creds)
    return service


def _encode_message(to_addr: str, subject: str, body: str, from_addr: str | None) -> str:
    msg = EmailMessage()
    msg["To"] = to_addr
    if from_addr:
        # Must be a verified/alias sender on the authorized Gmail account.
        msg["From"] = from_addr
    msg["Subject"] = subject
    msg.set_content(body)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")


# ---- Tool: send_email -------------------------------------------------------
@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """Send a plaintext email using the authorized Gmail account.

    Returns:
      - EMAIL_SENT: to=<addr>, id=<gmail_message_id>
      - ERROR: <message>
    """
    params = {"to": to, "subject": subject, "body_len": len(body)}
    try:
        # Minimal sanity check; Gmail will still validate.
        if "@" not in (to or ""):
            result = 'ERROR: Invalid "to" address.'
            _log_tool("send_email", params, result)
            return result

        service = _build_gmail_service()
        from_env = os.getenv("GMAIL_SENDER") or None
        raw_msg = _encode_message(to, subject, body, from_env)

        # Gmail API call
        resp = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_msg})
            .execute()
        )
        msg_id = (resp or {}).get("id") or "unknown"
        result = f"EMAIL_SENT: to={to}, id={msg_id}"
        _log_tool("send_email", params, result)
        return result
    except Exception as exc:  # pragma: no cover - network/credentials issues
        result = f"ERROR: {exc}"
        _log_tool("send_email", params, result)
        return result


# ---- Entrypoint -------------------------------------------------------------
if __name__ == "__main__":
    mode = "stdio"
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mode = "dev"
    _logger.info("Starting Gmail MCP server (mode=%s)", mode)
    if mode == "dev":
        mcp.run()
    else:
        mcp.run(transport="stdio")
