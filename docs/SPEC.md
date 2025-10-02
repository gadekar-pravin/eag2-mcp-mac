Below is a **complete programming specifications document** for the “MCP Keynote Drawing Agent (macOS)” project. It is written so an LLM engineer/agent can implement the entire solution end‑to‑end with minimal ambiguity.

---

# Programming Specifications — MCP Keynote Drawing Agent (macOS)

## 1. Objective & Deliverables

**Objective:**
Build an AI agent that, using **Model Context Protocol (MCP)** tools on macOS, opens **Keynote**, draws a **rectangle** on slide 1, and writes **user‑provided text inside the rectangle**. All UI actions must occur **via MCP tool calls made by the LLM**, not by manual client code.

**Primary Deliverables**

1. A working **MCP server** exposing Keynote automation tools for macOS.
2. A **client/orchestrator** (modification of `talk2mcp.py`) that:

   * Connects to the server via **stdio**,
   * Lists tools, injects a **strict function‑calling prompt**,
   * Iteratively executes LLM responses in the format `FUNCTION_CALL: name|arg1|...` until `FINAL_ANSWER`.
3. Logs that show **only** agent‑initiated tool usage led to the drawing.
4. A **short demo video** (screen recording) and a **README** describing how to run the project locally.
5. (Optional bonus) A **Gmail MCP server** with a `send_email` tool and a second short demo video.

**Non‑Goals**

* No Windows automation (`pywinauto`, `win32*`) — macOS only.
* No manual client‑side invocation of drawing tools after `FINAL_ANSWER`.

---

## 2. Target Platform & Assumptions

* **OS:** macOS (tested on Apple Silicon).
* **App:** Apple **Keynote** (latest).
* **Automation:** AppleScript via `osascript` (preferred) or PyObjC/ScriptingBridge (optional).
* **LLM:** Google **Gemini 2.0 Flash** via `google-genai` / `from google import genai`.
* **MCP:** `fastmcp` server (`mcp.server.fastmcp`), `mcp` client (`mcp.client.stdio`).

**Permissions Required**

* *System Settings → Privacy & Security → Accessibility*: allow Terminal/IDE (and Python)
* *System Settings → Privacy & Security → Automation*: allow Python to control Keynote

---

## 3. High‑Level Architecture

```
+------------------+            stdio           +--------------------------+
|  talk2mcp.py     |  <---------------------->  |  mcp_server_keynote.py   |
|  (MCP Client)    |                            |  (FastMCP server)        |
+------------------+                            +--------------------------+
        |                                                     |
        |                                       +------------v-----------+
        |                                       |   AppleScript/Keynote  |
        |                                       | (osascript subprocess) |
        |                                       +------------------------+
        |
        +--> Gemini 2.0 Flash (LLM) via google-genai
```

**Key principle:** All drawing must be caused by LLM‑originated `FUNCTION_CALL` lines that the client forwards to the MCP server tools.

---

## 4. Project Structure

```
eag2-mcp-mac/
├── README.md
├── .env.example
├── requirements.txt
├── Makefile
├── pyproject.toml                  # optional; or use requirements.txt only
├── docs/
│   └── SPEC.md                     # this document
├── logs/
│   └── agent.log                   # runtime logs (gitignored)
├── src/
│   ├── client/
│   │   ├── talk2mcp.py             # updated orchestrator (mac server target)
│   │   └── prompts.py              # system & query templates
│   ├── mcp_servers/
│   │   ├── mcp_server_keynote.py   # FastMCP Keynote server (main)
│   │   ├── applescript/
│   │   │   ├── open_keynote.applescript
│   │   │   ├── get_slide_size.applescript
│   │   │   ├── draw_rectangle.applescript
│   │   │   ├── add_text_in_keynote.applescript
│   │   │   └── export_slide_png.applescript
│   │   └── utils/
│   │       └── applescript_runner.py
│   └── gmail_bonus/                # optional
│       └── mcp_server_gmail.py     # send_email tool
├── tests/
│   ├── test_protocol.py            # FUNCTION_CALL parser tests
│   ├── test_server_contracts.py    # server return grammar tests (mocked)
│   └── test_applescript_smoke.py   # optional: local-only smoke tests
└── scripts/
    ├── dev_run_client.sh
    └── record_demo_checklist.md
```

> **Note:** keep `logs/` and any exported images out of version control via `.gitignore`.

---

## 5. Dependencies

**requirements.txt**

```txt
# Core
mcp>=0.2.0
fastmcp>=0.1.15

# Google AI (Gemini 2.0 Flash)
google-genai>=0.3.0

# Env & tooling
python-dotenv>=1.0.1
tenacity>=9.0.0

# Dev
pytest>=8.0.0
ruff>=0.6.0
mypy>=1.11.0
```

**Environment**

```
GEMINI_API_KEY="your-key-here"
LOG_LEVEL="INFO"
SCREENSHOT_PATH="/tmp/mcp_keynote_slide.png"  # optional feature
KEYNOTE_THEME="White"                          # default theme
KEYNOTE_DOCUMENT_MODE="reuse_or_create"        # or "always_new"
```

---

## 6. MCP Server — Tool Contracts (macOS Keynote)

Implement these **exact** tools in `mcp_server_keynote.py`. Use `fastmcp` and ensure the **names and parameter order** match below.

### 6.1 Common server state

* Keep a module‑level dict:

  ```python
  SERVER_STATE = {
      "last_rectangle_id": None,
      "last_slide_dims": {"width": None, "height": None}
  }
  ```
* Prefer **slide coordinates** (points), not screen pixels.

### 6.2 Tool: `open_keynote`

**Signature**

```python
@mcp.tool()
def open_keynote() -> str: ...
```

**Behavior**

* Activate Keynote.
* If `KEYNOTE_DOCUMENT_MODE == "always_new"`: create new document with theme `${KEYNOTE_THEME}`.
* Else reuse `document 1` if exists; otherwise create new.
* Select **slide 1**.
* Read **slide size** and cache in `SERVER_STATE["last_slide_dims"]`.

**Return (plain text)**

* Success:
  `KEYNOTE_READY: slide=1, slide_width=<number>, slide_height=<number>`
* Warning‑success:
  `KEYNOTE_READY_WITH_WARNING: slide=1, slide_width=<number>, slide_height=<number>, note=<string>`
* Error:
  `ERROR: <message>`

**AppleScript reference (stored in `src/mcp_servers/applescript/open_keynote.applescript`):**

```applescript
tell application "Keynote"
    activate
    set frontmost to true
    set docRef to missing value
    if (count of documents) = 0 then
        set docRef to make new document with properties {document theme:theme "White"}
    else
        set docRef to document 1
    end if
    tell docRef
        set currentSlide to slide 1
        set s to slide size
        set w to item 1 of s
        set h to item 2 of s
    end tell
end tell
return w & "|" & h
```

The Python wrapper will parse `w|h`.

---

### 6.3 Tool: `get_slide_size`

**Signature**

```python
@mcp.tool()
def get_slide_size() -> str: ...
```

**Behavior**

* Reads slide 1 size. Updates `SERVER_STATE["last_slide_dims"]`.

**Return**

* `SLIDE_SIZE: width=<number>, height=<number>`
* `ERROR: <message>`

**AppleScript:** `get_slide_size.applescript` (similar to the end of `open_keynote`).

---

### 6.4 Tool: `draw_rectangle`

**Signature**

```python
@mcp.tool()
def draw_rectangle(x: int, y: int, width: int, height: int) -> str: ...
```

**Behavior**

* Create a **rectangle shape** on slide 1 with the given bounds.
* Keep the shape selected; capture the shape’s **id**.
* Update `SERVER_STATE["last_rectangle_id"]`.

**Return**

* `RECTANGLE_OK: id=<string>, x=<number>, y=<number>, width=<number>, height=<number>`
* `ERROR: <message>`

**AppleScript (`draw_rectangle.applescript`):**

```applescript
-- Args passed as environment variables or concatenated string; wrapper parses
on run argv
    set xVal to (item 1 of argv) as integer
    set yVal to (item 2 of argv) as integer
    set wVal to (item 3 of argv) as integer
    set hVal to (item 4 of argv) as integer
    tell application "Keynote"
        tell document 1
            tell slide 1
                set newShape to make new shape with properties {shape type: rectangle, position:{xVal, yVal}, width:wVal, height:hVal}
                set theID to id of newShape
            end tell
        end tell
    end tell
    return theID
end run
```

---

### 6.5 Tool: `add_text_in_keynote`

**Signature**

```python
@mcp.tool()
def add_text_in_keynote(text: str) -> str: ...
```

**Behavior**

* If `SERVER_STATE["last_rectangle_id"]` is missing: return `ERROR` instructing caller to draw a rectangle first.
* Set the **shape’s object text** to `text` (convert `¦` back to `|` if present; LLM was told to avoid `|`).
* Optionally center the text horizontally & vertically.

**Return**

* `TEXT_OK: id=<string>, characters=<integer>`
* `ERROR: <message>`

**AppleScript (`add_text_in_keynote.applescript`):**

```applescript
on run argv
    set theID to (item 1 of argv)
    set theText to (item 2 of argv)
    tell application "Keynote"
        tell document 1
            tell slide 1
                set targetShape to (first shape whose id is theID)
                set object text of targetShape to theText
                -- Optional: center align
                tell object text of targetShape
                    set alignment to center
                end tell
            end tell
        end tell
    end tell
    return (length of theText) as integer
end run
```

---

### 6.6 (Optional) Tool: `screenshot_slide`

**Signature**

```python
@mcp.tool()
def screenshot_slide(path: str) -> str: ...
```

**Behavior**

* Export slide 1 as PNG to `path` (create dirs if needed).

**Return**

* `SCREENSHOT_SAVED: path=<string>`
* `ERROR: <message>`

**AppleScript (`export_slide_png.applescript`):**

```applescript
on run argv
    set outPath to (item 1 of argv)
    tell application "Keynote"
        tell document 1
            set t to POSIX file outPath
            export it to t as PNG with properties {slides:{1}, resolution:144}
        end tell
    end tell
    return outPath
end run
```

---

### 6.7 AppleScript Runner Utility

**`src/mcp_servers/utils/applescript_runner.py` (skeleton)**

```python
import subprocess
from typing import List

class AppleScriptError(RuntimeError):
    pass

def run_applescript_file(path: str, args: List[str] | None = None, timeout: int = 10) -> str:
    cmd = ["osascript", path]
    if args:
        cmd.extend(args)
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout)
        return out.decode("utf-8").strip()
    except subprocess.CalledProcessError as e:
        raise AppleScriptError(e.output.decode("utf-8", errors="ignore"))
```

---

### 6.8 `mcp_server_keynote.py` (skeleton/shape)

```python
from mcp.server.fastmcp import FastMCP
from typing import Optional, Dict
import os
from .utils.applescript_runner import run_applescript_file, AppleScriptError

mcp = FastMCP("KeynoteMCP")

SERVER_STATE: Dict[str, object] = {
    "last_rectangle_id": None,
    "last_slide_dims": {"width": None, "height": None}
}

APP_DIR = os.path.dirname(__file__)
AS_DIR = os.path.join(APP_DIR, "applescript")

def _as(path): return os.path.join(AS_DIR, path)

@mcp.tool()
def open_keynote() -> str:
    try:
        wh = run_applescript_file(_as("open_keynote.applescript"))
        w, h = [int(float(x)) for x in wh.split("|")]
        SERVER_STATE["last_slide_dims"] = {"width": w, "height": h}
        return f"KEYNOTE_READY: slide=1, slide_width={w}, slide_height={h}"
    except Exception as e:
        return f"ERROR: {e}"

@mcp.tool()
def get_slide_size() -> str:
    try:
        wh = run_applescript_file(_as("get_slide_size.applescript"))
        w, h = [int(float(x)) for x in wh.split("|")]
        SERVER_STATE["last_slide_dims"] = {"width": w, "height": h}
        return f"SLIDE_SIZE: width={w}, height={h}"
    except Exception as e:
        return f"ERROR: {e}"

@mcp.tool()
def draw_rectangle(x: int, y: int, width: int, height: int) -> str:
    try:
        rect_id = run_applescript_file(
            _as("draw_rectangle.applescript"),
            [str(x), str(y), str(width), str(height)]
        )
        SERVER_STATE["last_rectangle_id"] = rect_id
        return f"RECTANGLE_OK: id={rect_id}, x={x}, y={y}, width={width}, height={height}"
    except Exception as e:
        return f"ERROR: {e}"

@mcp.tool()
def add_text_in_keynote(text: str) -> str:
    rect_id = SERVER_STATE.get("last_rectangle_id")
    if not rect_id:
        return "ERROR: No rectangle context. Call draw_rectangle first."
    # Replace LLM sanitization char back to pipe if present
    safe_text = text.replace("¦", "|")
    try:
        count = run_applescript_file(_as("add_text_in_keynote.applescript"), [str(rect_id), safe_text])
        return f"TEXT_OK: id={rect_id}, characters={int(count)}"
    except Exception as e:
        return f"ERROR: {e}"

@mcp.tool()
def screenshot_slide(path: str) -> str:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        out = run_applescript_file(_as("export_slide_png.applescript"), [path])
        return f"SCREENSHOT_SAVED: path={out}"
    except Exception as e:
        return f"ERROR: {e}"

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()
    else:
        mcp.run(transport="stdio")
```

> **Implementation note:** The above is a **skeleton** to clarify structure, public interfaces, and return grammar. The LLM should fill in any small gaps while keeping contracts intact.

---

## 7. Client Orchestrator (`talk2mcp.py`) Requirements

**Starting point:** The provided `talk2mcp.py` file.

**Mandatory Changes**

1. **Point to the mac server**:

   ```python
   server_params = StdioServerParameters(
       command="python",
       args=["-u", "src/mcp_servers/mcp_server_keynote.py"]
   )
   ```
2. **Remove any manual drawing after `FINAL_ANSWER`**
   Delete the block that calls `open_paint`, `draw_rectangle`, etc. The agent must call all tools itself.
3. **Remove `pdb.set_trace()`** breakpoints.
4. **Increase iterations**: `max_iterations = 6` (or 8) to allow: open → size → draw → text → (optional screenshot) → finalize.
5. **Logging**: Write all input/output lines and tool results to `logs/agent.log`.

**Function‑Call Protocol (unchanged)**

* The LLM must respond each turn with **exactly one** of:

  ```
  FUNCTION_CALL: function_name|param1|param2|...
  FINAL_ANSWER: [done]
  ```
* Robustly parse only the first matching line if multiple lines are returned.

**Type Conversion**

* Use the tool’s `inputSchema` to map:

  * `integer` → `int(value)`
  * `number` → `float(value)` but cast to `int` for coordinates
  * `string` → raw string (do not strip spaces; sanitize only newlines and `|` if needed)

**Resilience**

* If LLM returns an unrecognized tool: log & add a message back to the LLM in the next turn saying `Unknown tool <name>. Available: ...` (your system prompt should make this rare).
* If a tool returns `ERROR: ...`: keep the error text in the running transcript so the LLM can adjust parameters on the next turn.

---

## 8. Prompts (System + Query)

**`src/client/prompts.py`**

```python
SYSTEM_PROMPT = """You are a macOS Keynote drawing agent that must accomplish a concrete UI goal by calling MCP tools.
Your job: open Keynote, draw ONE rectangle centered on slide 1, and write the user-provided text inside that rectangle.
You MUST accomplish this ONLY by calling the available tools. Do NOT describe what you will do. Do NOT emit explanations.

Rules:
- You must respond with EXACTLY ONE SINGLE LINE each turn, in one of these formats:
  1) FUNCTION_CALL: function_name|param1|param2|...
  2) FINAL_ANSWER: [done]
- Never output anything before or after that one line. No markdown. No prose.
- Begin by calling open_keynote (or, if available, get_slide_size after opening) to discover slide dimensions.
- Then call draw_rectangle with numeric slide coordinates (not pixels). If you know the slide size, choose a centered rectangle that is ~60% of slide width and ~30% of slide height.
  Let W=slide_width and H=slide_height:
    rect_width = round(0.6*W)
    rect_height = round(0.3*H)
    x = round((W - rect_width)/2)
    y = round((H - rect_height)/2)
- Then call add_text_in_keynote with the EXACT text the user asked you to write (no quotes, no extra words).
- If any tool returns an ERROR, adjust parameters and retry at most once.
- Never call the same tool twice with the same parameters.
- Parameter formatting:
  * Numbers: plain (no commas, no units).
  * Strings: do not include the '|' character. If input text contains '|', replace it with '¦'.
  * Keep everything on a single line; do not insert newlines in arguments.
- Stop when the text has been placed inside the rectangle and respond with: FINAL_ANSWER: [done]

Available tools:
{tools_description}

Remember: only use FUNCTION_CALL or FINAL_ANSWER lines. Nothing else.
"""

# Example query to seed the run (the client may override this)
DEFAULT_QUERY = "Create a rectangle in Keynote slide 1 and write this exact text inside it: Hello from MCP on macOS."
```

---

## 9. Return Grammar (Server → Client)

**All return values are plain text**. The client does not parse them beyond logging; they are for human audit and optional LLM reading.

* `KEYNOTE_READY: slide=1, slide_width=<number>, slide_height=<number>`
* `KEYNOTE_READY_WITH_WARNING: slide=1, slide_width=<number>, slide_height=<number>, note=<string>`
* `SLIDE_SIZE: width=<number>, height=<number>`
* `RECTANGLE_OK: id=<string>, x=<number>, y=<number>, width=<number>, height=<number>`
* `TEXT_OK: id=<string>, characters=<integer>`
* `SCREENSHOT_SAVED: path=<string>`
* `ERROR: <message>`

---

## 10. Logging & Observability

* **Client** (`talk2mcp.py`):

  * Log: model prompts (system + user), raw LLM responses, parsed `FUNCTION_CALL`, tool result payloads, and a final summary.
  * File: `logs/agent.log`. Use UTC timestamps; include a `run_id`.
* **Server**:

  * Log: tool name, parameters, AppleScript runner output, elapsed time, and return string.
  * Consider a decorator to time each tool.

**Sample log lines**

```
[2025-10-02T12:01:07Z][client][run_id=abc123] FUNCTION_CALL parsed: draw_rectangle|384|378|1152|324
[2025-10-02T12:01:08Z][server][tool=draw_rectangle] args={'x':384,'y':378,'width':1152,'height':324} -> RECTANGLE_OK: id=ABCD-1234, x=384, y=378, width=1152, height=324
```

---

## 11. Testing & Acceptance Criteria

**Core Acceptance (must pass)**

1. Running the client produces this **sequence of tool calls** (order may include `get_slide_size`):

   * `open_keynote`
   * `draw_rectangle|x|y|width|height` (centered ~60% x ~30% rule)
   * `add_text_in_keynote|<exact user text>`
   * `FINAL_ANSWER: [done]`
2. The rectangle and text appear on **Keynote slide 1**.
3. **No manual calls** from client after `FINAL_ANSWER`.
4. Logs clearly show each call and its result.
5. Project runs from a fresh clone with documented steps.

**Negative/Edge Cases**

* If Keynote is closed: `open_keynote` must start it and return slide size.
* If a tool returns `ERROR`, the next LLM step should adjust once and retry (per system rules).
* If text includes `|`, the LLM replaces with `¦`; server reverses it.

**Optional Acceptance**

* `screenshot_slide` saves a PNG to `${SCREENSHOT_PATH}`.
* Gmail bonus: `send_email(to, subject, body, body_html?)` demonstration.

---

## 12. Build & Run

**Makefile**

```make
.PHONY: setup run-client run-server-dev lint test

setup:
\tpython -m venv .venv
\t. .venv/bin/activate && pip install -U pip && pip install -r requirements.txt

run-client:
\t. .venv/bin/activate && python src/client/talk2mcp.py

run-server-dev:
\t. .venv/bin/activate && python src/mcp_servers/mcp_server_keynote.py dev

lint:
\t. .venv/bin/activate && ruff check .

test:
\t. .venv/bin/activate && pytest -q
```

**Run sequence**

1. `cp .env.example .env` and fill `GEMINI_API_KEY`.
2. `make setup`
3. `make run-client`

---

## 13. Bonus: Gmail MCP (Optional)

**File:** `src/gmail_bonus/mcp_server_gmail.py`
**Tool:** `send_email(to: str, subject: str, body: str, body_html?: str) -> str`
**Behavior:** Uses Gmail API / OAuth to send email, returning plaintext with an optional HTML alternative:

* `EMAIL_SENT: to=<addr>, id=<gmail_message_id>`
* `ERROR: <message>`

**Scopes:** `https://www.googleapis.com/auth/gmail.send`
**Notes:** Provide a small README for OAuth setup (credentials.json, token.json).

---

## 14. Security & Privacy

* Store keys in `.env` only; never commit secrets.
* The server should not expose filesystem beyond explicit paths given to tools.
* AppleScript code must only address Keynote and the current document.

---

## 15. Implementation Tasks (for the LLM Agent)

1. **Scaffold** the repository per the structure in §4; add `.gitignore` for `.venv`, `logs/`, and exported images.
2. **Implement** `applescript_runner.py`.
3. **Author** the AppleScript files in `src/mcp_servers/applescript/` as in §6.
4. **Implement** `mcp_server_keynote.py` tools adhering to contracts in §6.
5. **Modify** `src/client/talk2mcp.py`:

   * Point to `mcp_server_keynote.py`,
   * Remove manual calls after `FINAL_ANSWER`,
   * Remove `pdb.set_trace()`,
   * Increase iteration budget,
   * Add file logging to `logs/agent.log`.
6. **Add** `src/client/prompts.py` with `SYSTEM_PROMPT` and `DEFAULT_QUERY` in §8; ensure injection of `{tools_description}`.
7. **Write** tests in `tests/` to validate output grammar and parsing (mock server where feasible).
8. **Document** in `README.md`: setup, permissions, run steps, and recording instructions.
9. **Record** a short demo: terminal + Keynote window; show logs scrolling and the rectangle+text appearing.
10. **(Optional)** Implement Gmail MCP and record second video.

---

## 16. Troubleshooting

* **Keynote not responding:** Open Keynote once manually; ensure Python has **Automation** permission.
* **AppleScript errors:** Print the raw `osascript` output; many errors include line numbers.
* **No rectangle appears:** Ensure slide coordinates are **within** slide size; verify W/H and recompute center.
* **Text not visible:** Ensure the text is set on the **shape’s object text**, not a new text box; check fill color vs slide theme.
* **Pipes in text:** LLM must replace `|` with `¦`; server reverses.

---

## 17. Example Good Run (Expected Log Trace)

```
[client] tools listed: open_keynote, get_slide_size, draw_rectangle, add_text_in_keynote, screenshot_slide
[client] LLM => FUNCTION_CALL: open_keynote
[server] KEYNOTE_READY: slide=1, slide_width=1920, slide_height=1080
[client] LLM => FUNCTION_CALL: draw_rectangle|384|378|1152|324
[server] RECTANGLE_OK: id=ABCD-1234, x=384, y=378, width=1152, height=324
[client] LLM => FUNCTION_CALL: add_text_in_keynote|Hello from MCP on macOS.
[server] TEXT_OK: id=ABCD-1234, characters=26
[client] LLM => FINAL_ANSWER: [done]
```

---

## 18. Quality Bar

* **Determinism:** Given the same slide size, the rectangle coordinates are computed consistently (~60%×~30% centered).
* **Auditability:** Logs alone make it clear that the agent, not the client, performed all drawing actions.
* **Portability:** No Windows‑specific imports; only macOS and Keynote required.
* **Clarity:** All tool contracts and return strings strictly follow this spec.

---

**End of SPEC**
