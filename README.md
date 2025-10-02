# MCP Keynote Drawing Agent (macOS)

This project implements a full Model Context Protocol (MCP) workflow that allows an LLM agent to open Keynote on macOS, draw a centered rectangle on slide 1, and insert user-provided text inside that rectangle. All desktop automation happens through AppleScript tools exposed by a FastMCP server. A Gemini 2.0 Flash model drives the interaction via the `mcp` stdio client.

## Repository Layout

```
eag2-mcp-mac/
├── Makefile
├── README.md
├── requirements.txt
├── .env.example
├── docs/
│   └── SPEC.md
├── logs/
├── scripts/
│   ├── dev_run_client.sh
│   └── record_demo_checklist.md
├── src/
│   ├── client/
│   │   ├── __init__.py
│   │   ├── prompts.py
│   │   └── talk2mcp.py
│   ├── gmail_bonus/
│   │   └── __init__.py
│   └── mcp_servers/
│       ├── __init__.py
│       ├── mcp_server_keynote.py
│       ├── applescript/
│       │   ├── add_text_in_keynote.applescript
│       │   ├── draw_rectangle.applescript
│       │   ├── export_slide_png.applescript
│       │   ├── get_slide_size.applescript
│       │   └── open_keynote.applescript
│       └── utils/
│           ├── __init__.py
│           └── applescript_runner.py
└── tests/
    ├── conftest.py
    ├── test_applescript_smoke.py
    ├── test_protocol.py
    └── test_server_contracts.py
```

## Prerequisites

- macOS with Apple Keynote installed (tested on Apple Silicon).
- Python 3.11+
- Gemini 2.0 Flash API access (`google-genai`).
- Accessibility + Automation privileges for the terminal/IDE that launches the Python scripts.

## Setup

1. Clone the repository and navigate into it.
2. Copy the example environment file and set your Gemini key:
   ```bash
   cp .env.example .env
   # edit .env and place your GEMINI_API_KEY
   ```
3. Install dependencies into a virtual environment:
   ```bash
   make setup
   ```

## macOS Permissions

AppleScript automation requires explicit permission:

1. Open **System Settings → Privacy & Security → Accessibility** and add Terminal (or your IDE) and `Python.app` from the project’s virtual environment (`.venv/bin/python`).
2. Open **System Settings → Privacy & Security → Automation** and ensure the terminal/IDE is allowed to control Keynote.
3. Launch Keynote once manually so it can request approval the first time automation runs.

## Running the Agent

1. Ensure Keynote is closed or has a document ready (the server will reuse document 1 or create a new one based on `KEYNOTE_DOCUMENT_MODE`).
2. Start the client orchestrator:
   ```bash
   make run-client
   # or: scripts/dev_run_client.sh --query "Custom instruction"
   ```
3. Watch the terminal logs (also written to `logs/agent.log`) to confirm the sequence:
   - `open_keynote`
   - optional `get_slide_size`
   - `draw_rectangle`
   - `add_text_in_keynote`
   - `FINAL_ANSWER: [done]`
4. The rectangle and text should appear on Keynote slide 1 without manual intervention after `FINAL_ANSWER`.

### Logging

- All client-side I/O is streamed to `logs/agent.log` with UTC timestamps and a per-run identifier.
- The server logs each tool invocation, including parameters, raw AppleScript output, and the final return string.

### Optional Screenshot Tool

The `screenshot_slide` tool exports slide 1 as a PNG. Provide a target path when instructing the agent, or set `SCREENSHOT_PATH` in `.env` and include that in the conversation.

## Tests

Run the automated test suite:

```bash
make test
```

Included coverage:

- `test_protocol.py` validates parsing of the strict FUNCTION_CALL/FINAL_ANSWER grammar.
- `test_server_contracts.py` patches the AppleScript runner to verify tool responses and server state management.
- `test_applescript_smoke.py` confirms the AppleScript files exist (skipped if Keynote automation is unavailable).

## Troubleshooting

- **Keynote not opening / permissions errors:** Re-check Accessibility & Automation settings. macOS may need to be restarted after toggling them.
- **AppleScript failures:** Review the terminal output; the server surfaces the raw error message from `osascript` in the return string and logs.
- **Rectangle not centered:** Ensure the slide dimensions are retrieved (`open_keynote` caches them) before `draw_rectangle` runs.
- **Pipes in text:** The agent replaces `|` with `¦` before calling `add_text_in_keynote`. The server converts it back automatically.
- **Gemini quota or auth issues:** Confirm `GEMINI_API_KEY` is valid and not rate limited.

## Demo Recording

Use `scripts/record_demo_checklist.md` as a quick reminder when producing the acceptance video. Capture both the CLI logs and the Keynote window in a single take.

