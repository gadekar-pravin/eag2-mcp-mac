import asyncio
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession


async def main():
    params = StdioServerParameters(
        command="python",
        args=["-u", "src/gmail_bonus/mcp_server_gmail.py"],
    )
    async with stdio_client(params) as (rs, ws):
        async with ClientSession(read_stream=rs, write_stream=ws) as session:
            await session.initialize()
            resp = await session.call_tool(
                "send_email",
                {
                    "to": "pbgadekar@gmail.com",
                    "subject": "MCP Hello - EAG V2 Assignment 4",
                    "body": "Sent from the Gmail MCP server.",
                },
            )
            # The FastMCP client returns an object with .content; print text parts
            out = []
            for c in getattr(resp, "content", []):
                if getattr(c, "type", "") == "text":
                    out.append(c.text)
            print("\n".join(out) if out else str(resp))


if __name__ == "__main__":
    asyncio.run(main())
