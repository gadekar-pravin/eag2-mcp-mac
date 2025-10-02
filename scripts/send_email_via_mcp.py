"""Send the agent log email via the Gmail MCP server."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from client.email_payload import LOG_PATH, build_log_email_payload


async def main() -> None:
    params = StdioServerParameters(
        command="python",
        args=["-u", "src/gmail_bonus/mcp_server_gmail.py"],
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream=read_stream, write_stream=write_stream) as session:
            await session.initialize()
            payload = build_log_email_payload(log_path=LOG_PATH)
            resp = await session.call_tool("send_email", payload)
            out = []
            for item in getattr(resp, "content", []):
                if getattr(item, "type", "") == "text":
                    out.append(item.text)
            print("\n".join(out) if out else str(resp))


if __name__ == "__main__":
    asyncio.run(main())
