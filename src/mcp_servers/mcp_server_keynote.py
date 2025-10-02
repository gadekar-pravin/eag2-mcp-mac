"""FastMCP server exposing Keynote automation tools for macOS."""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

if __package__ is None or __package__ == "":  # pragma: no cover
    CURRENT_DIR = Path(__file__).resolve().parent
    SRC_ROOT = CURRENT_DIR.parent
    if str(SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT))
    from mcp_servers.utils.applescript_runner import AppleScriptError, run_applescript_file
else:
    from .utils.applescript_runner import AppleScriptError, run_applescript_file

mcp = FastMCP("KeynoteMCP")

SERVER_STATE: Dict[str, Any] = {
    "last_rectangle_id": None,
    "last_slide_dims": {"width": None, "height": None},
}

APP_DIR = Path(__file__).resolve().parent
AS_DIR = APP_DIR / "applescript"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_logger = logging.getLogger("keynote_mcp_server")
if not _logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)sZ][server][%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
_logger.setLevel(LOG_LEVEL)


def _as(path: str) -> str:
    return str(AS_DIR / path)


def _log_tool(name: str, params: Dict[str, Any], result: str, start: float, raw: str | None = None) -> None:
    duration = time.perf_counter() - start
    payload = {
        "params": params,
        "result": result,
        "elapsed": round(duration, 4),
    }
    if raw is not None:
        payload["raw"] = raw
    _logger.info("tool=%s %s", name, payload)


def _parse_dimensions(raw: str) -> tuple[int, int]:
    parts = [p for p in raw.split("|") if p]
    if len(parts) < 2:
        raise ValueError(f"Unexpected slide size payload: {raw}")
    width = int(float(parts[0]))
    height = int(float(parts[1]))
    return width, height


@mcp.tool()
def open_keynote() -> str:
    start = time.perf_counter()
    result = "ERROR: Unknown failure"
    raw = None
    theme = os.getenv("KEYNOTE_THEME", "White")
    mode = os.getenv("KEYNOTE_DOCUMENT_MODE", "reuse_or_create").strip().lower()
    params = {"theme": theme, "mode": mode}
    try:
        if mode not in {"reuse_or_create", "always_new"}:
            mode = "reuse_or_create"
            params["mode"] = mode
        raw = run_applescript_file(_as("open_keynote.applescript"), [theme, mode])
        width, height = _parse_dimensions(raw)
        SERVER_STATE["last_slide_dims"] = {"width": width, "height": height}
        if raw.count("|") >= 2:
            note = raw.split("|", 2)[2]
            result = (
                f"KEYNOTE_READY_WITH_WARNING: slide=1, slide_width={width}, "
                f"slide_height={height}, note={note}"
            )
        else:
            result = f"KEYNOTE_READY: slide=1, slide_width={width}, slide_height={height}"
    except (AppleScriptError, ValueError) as exc:
        result = f"ERROR: {exc}"
    except Exception as exc:  # pragma: no cover - safeguard
        result = f"ERROR: {exc}"
    finally:
        _log_tool("open_keynote", params, result, start, raw)
    return result


@mcp.tool()
def get_slide_size() -> str:
    start = time.perf_counter()
    result = "ERROR: Unknown failure"
    raw = None
    try:
        raw = run_applescript_file(_as("get_slide_size.applescript"))
        width, height = _parse_dimensions(raw)
        SERVER_STATE["last_slide_dims"] = {"width": width, "height": height}
        result = f"SLIDE_SIZE: width={width}, height={height}"
    except (AppleScriptError, ValueError) as exc:
        result = f"ERROR: {exc}"
    except Exception as exc:  # pragma: no cover - safeguard
        result = f"ERROR: {exc}"
    finally:
        _log_tool("get_slide_size", {}, result, start, raw)
    return result


@mcp.tool()
def draw_rectangle(x: int, y: int, width: int, height: int) -> str:
    start = time.perf_counter()
    result = "ERROR: Unknown failure"
    raw = None
    params = {"x": x, "y": y, "width": width, "height": height}
    try:
        raw = run_applescript_file(
            _as("draw_rectangle.applescript"),
            [str(x), str(y), str(width), str(height)],
        )
        rect_id = raw.strip()
        SERVER_STATE["last_rectangle_id"] = rect_id
        result = (
            f"RECTANGLE_OK: id={rect_id}, x={x}, y={y}, "
            f"width={width}, height={height}"
        )
    except AppleScriptError as exc:
        result = f"ERROR: {exc}"
    except Exception as exc:  # pragma: no cover - safeguard
        result = f"ERROR: {exc}"
    finally:
        _log_tool("draw_rectangle", params, result, start, raw)
    return result


@mcp.tool()
def add_text_in_keynote(text: str) -> str:
    start = time.perf_counter()
    result = "ERROR: Unknown failure"
    raw = None
    rect_id = SERVER_STATE.get("last_rectangle_id")
    params = {"text": text, "rectangle_id": rect_id}
    if not rect_id:
        result = "ERROR: No rectangle context. Call draw_rectangle first."
        _log_tool("add_text_in_keynote", params, result, start, raw)
        return result

    safe_text = text.replace("¦", "|")
    params["text"] = safe_text
    try:
        raw = run_applescript_file(
            _as("add_text_in_keynote.applescript"),
            [str(rect_id), safe_text],
        )
        try:
            char_count = int(float(raw))
        except ValueError:
            char_count = len(safe_text)
        result = f"TEXT_OK: id={rect_id}, characters={char_count}"
    except AppleScriptError as exc:
        result = f"ERROR: {exc}"
    except Exception as exc:  # pragma: no cover - safeguard
        result = f"ERROR: {exc}"
    finally:
        _log_tool("add_text_in_keynote", params, result, start, raw)
    return result


@mcp.tool()
def screenshot_slide(path: str) -> str:
    start = time.perf_counter()
    result = "ERROR: Unknown failure"
    raw = None
    expanded_path = os.path.abspath(os.path.expanduser(path))
    params = {"path": expanded_path}
    try:
        directory = os.path.dirname(expanded_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        raw = run_applescript_file(_as("export_slide_png.applescript"), [expanded_path])
        result = f"SCREENSHOT_SAVED: path={raw}"
    except AppleScriptError as exc:
        result = f"ERROR: {exc}"
    except Exception as exc:  # pragma: no cover - safeguard
        result = f"ERROR: {exc}"
    finally:
        _log_tool("screenshot_slide", params, result, start, raw)
    return result


if __name__ == "__main__":
    import sys

    mode = "stdio"
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mode = "dev"

    _logger.info("Starting Keynote MCP server (mode=%s)", mode)
    if mode == "dev":
        mcp.run()
    else:
        mcp.run(transport="stdio")
