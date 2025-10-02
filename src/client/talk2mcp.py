"""Client orchestrator that drives the Keynote MCP server via Gemini."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple
from uuid import uuid4

from dotenv import load_dotenv
from google import genai

try:  # pragma: no cover - handled at runtime
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
except ImportError as exc:  # pragma: no cover - guidance for setup
    raise RuntimeError(
        "The 'mcp' package is required. Install dependencies with `pip install -r requirements.txt`."
    ) from exc

# Allow running as a script (python src/client/talk2mcp.py)
if __package__ is None or __package__ == "":  # pragma: no cover
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    SRC_ROOT = PROJECT_ROOT / "src"
    if str(SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT))
    from client.prompts import DEFAULT_QUERY, SYSTEM_PROMPT
else:
    from .prompts import DEFAULT_QUERY, SYSTEM_PROMPT


FUNCTION_CALL_PREFIX = "FUNCTION_CALL:"
FINAL_ANSWER_LINE = "FINAL_ANSWER: [done]"
DEFAULT_MODEL = "gemini-2.0-flash"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOGS_DIR / "agent.log"


@dataclass
class AgentDirective:
    kind: str
    name: str | None = None
    arguments: List[str] | None = None


def parse_agent_line(line: str) -> AgentDirective:
    """Parse a FUNCTION_CALL or FINAL_ANSWER line from the LLM."""

    if not line:
        raise ValueError("Empty response line from agent")

    stripped = line.strip()
    if stripped.startswith(FUNCTION_CALL_PREFIX):
        payload = stripped[len(FUNCTION_CALL_PREFIX) :].strip()
        if not payload:
            raise ValueError("FUNCTION_CALL missing payload")
        parts = payload.split("|")
        name = parts[0].strip()
        args = [part.strip() for part in parts[1:]] if len(parts) > 1 else []
        if not name:
            raise ValueError("FUNCTION_CALL missing function name")
        return AgentDirective(kind="function_call", name=name, arguments=args)

    if stripped == FINAL_ANSWER_LINE:
        return AgentDirective(kind="final_answer")

    raise ValueError(f"Unrecognized agent directive: {line}")


def _ensure_logs_dir() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]


class RunLogger:
    """Simple logger that writes structured lines to stdout and agent.log."""

    def __init__(self, run_id: str) -> None:
        _ensure_logs_dir()
        self.run_id = run_id
        self._file_handle = open(LOG_FILE, "a", encoding="utf-8")

    def close(self) -> None:
        try:
            self._file_handle.close()
        except Exception:  # pragma: no cover - best effort cleanup
            pass

    def log(self, message: str) -> None:
        timestamp = _utc_timestamp()
        line = f"[{timestamp}Z][client][run_id={self.run_id}] {message}"
        print(line)
        self._file_handle.write(f"{line}\n")
        self._file_handle.flush()

    def __enter__(self) -> "RunLogger":  # pragma: no cover - convenience
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - convenience
        self.close()


def _extract_schema(tool: Any) -> List[Tuple[str, str]]:
    schema = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None)
    if not isinstance(schema, dict):
        return []
    properties = schema.get("properties", {})
    required = schema.get("required") or []
    ordered: List[Tuple[str, str]] = []
    for name in required:
        meta = properties.get(name, {})
        ordered.append((name, meta.get("type", "string")))
    for name, meta in properties.items():
        if name not in required:
            ordered.append((name, meta.get("type", "string")))
    return ordered


def _build_tools_description(tools: Sequence[Any]) -> Tuple[str, Dict[str, List[Tuple[str, str]]]]:
    descriptions: List[str] = []
    schemas: Dict[str, List[Tuple[str, str]]] = {}
    for tool in tools:
        name = getattr(tool, "name", "unknown")
        description = getattr(tool, "description", "") or "No description"
        schema = _extract_schema(tool)
        schemas[name] = schema
        if schema:
            params = ", ".join(f"{param}: {ptype}" for param, ptype in schema)
        else:
            params = "no parameters"
        descriptions.append(f"- {name}({params}) -> {description}")
    return "\n".join(descriptions), schemas


def _convert_argument(value: str, schema_type: str) -> Any:
    if schema_type == "integer":
        return int(value)
    if schema_type == "number":
        as_float = float(value)
        if as_float.is_integer():
            return int(as_float)
        return as_float
    return value


def _extract_response_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    candidates = getattr(response, "candidates", None)
    if candidates:
        candidate = candidates[0]
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content is not None else None
        if isinstance(parts, list):
            fragments: List[str] = []
            for part in parts:
                if hasattr(part, "text") and isinstance(part.text, str):
                    fragments.append(part.text)
                elif isinstance(part, dict) and isinstance(part.get("text"), str):
                    fragments.append(part["text"])
            if fragments:
                return "".join(fragments).strip()
    return str(response).strip()


def _generate_model_response(
    genai_client: Any,
    model: str,
    contents: Sequence[Dict[str, Any]],
    system_prompt: str,
) -> Any:
    """Dispatch to whichever google-genai response API is available."""

    responses_api = getattr(genai_client, "responses", None)
    if responses_api is not None:
        try:
            return responses_api.create(
                model=model,
                contents=contents,
                system_instruction=system_prompt,
                generation_config={"response_mime_type": "text/plain"},
            )
        except TypeError:
            return responses_api.create(
                model=model,
                contents=contents,
                system_instruction=system_prompt,
                config={"response_mime_type": "text/plain"},
            )

    models_api = getattr(genai_client, "models", None)
    if models_api is None:
        raise RuntimeError("google-genai client is missing both responses and models APIs")

    config_payload: Dict[str, Any] = {
        "system_instruction": system_prompt,
        "response_mime_type": "text/plain",
    }

    try:
        return models_api.generate_content(
            model=model,
            contents=contents,
            config=config_payload,
        )
    except TypeError:
        return models_api.generate_content(
            model=model,
            contents=contents,
            generation_config=config_payload,
        )


async def _call_tool(session: Any, tool_name: str, arguments: Dict[str, Any]) -> str:
    response = await session.call_tool(tool_name, arguments)
    # The MCP client returns an object with ``content``; fall back to str if needed.
    if hasattr(response, "content"):
        pieces: List[str] = []
        for item in response.content:
            if hasattr(item, "text") and item.text is not None:
                pieces.append(item.text)
            elif isinstance(item, dict) and item.get("type") == "text":
                pieces.append(item.get("text", ""))
        if pieces:
            return "\n".join(pieces).strip()
    return str(response).strip()


async def run_agent(query: str, max_iterations: int, model: str) -> None:
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Create a .env file per README instructions.")

    server_params = StdioServerParameters(
        command="python",
        args=["-u", str(PROJECT_ROOT / "src" / "mcp_servers" / "mcp_server_keynote.py")],
    )

    run_id = uuid4().hex[:8]
    logger = RunLogger(run_id)

    genai_client = genai.Client(api_key=api_key)

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream=read_stream, write_stream=write_stream) as session:
                await session.initialize()

                tools_result = await session.list_tools()
                tools = getattr(tools_result, "tools", tools_result)
                tools_description, tool_schemas = _build_tools_description(tools)
                system_prompt = SYSTEM_PROMPT.format(tools_description=tools_description)
                logger.log(f"tools listed: {', '.join(getattr(tool, 'name', 'unknown') for tool in tools)}")

                history: List[Dict[str, Any]] = []
                next_message = query

                for iteration in range(1, max_iterations + 1):
                    history.append({"role": "user", "parts": [{"text": next_message}]})
                    logger.log(f"iteration={iteration} user_message={next_message}")

                    response = _generate_model_response(genai_client, model, history, system_prompt)

                    raw_text = _extract_response_text(response)
                    primary_line = raw_text.splitlines()[0] if raw_text else ""
                    history.append({"role": "model", "parts": [{"text": primary_line}]})
                    logger.log(f"model_response={primary_line}")

                    try:
                        directive = parse_agent_line(primary_line)
                    except ValueError as exc:
                        feedback = f"Unrecognized response ({exc}). Please follow the protocol."
                        next_message = feedback
                        logger.log(f"protocol_error={exc}")
                        continue

                    if directive.kind == "final_answer":
                        logger.log("Agent signaled FINAL_ANSWER")
                        break

                    tool_name = directive.name or ""
                    raw_args = directive.arguments or []
                    schema = tool_schemas.get(tool_name, [])
                    if len(raw_args) != len(schema):
                        # Fall back to treating all args as strings if schema mismatched
                        logger.log(
                            f"argument_mismatch tool={tool_name} expected={len(schema)} received={len(raw_args)}"
                        )
                    arguments: Dict[str, Any] = {}
                    for idx, raw_arg in enumerate(raw_args):
                        if idx < len(schema):
                            key, expected_type = schema[idx]
                        else:
                            key, expected_type = f"arg{idx}", "string"
                        try:
                            arguments[key] = _convert_argument(raw_arg, expected_type)
                        except ValueError as exc:
                            logger.log(
                                f"argument_parse_error tool={tool_name} arg={key} value={raw_arg} error={exc}"
                            )
                            arguments[key] = raw_arg

                    logger.log(f"FUNCTION_CALL parsed: {tool_name}|{'|'.join(raw_args)}")

                    if not hasattr(session, "call_tool"):
                        raise RuntimeError("MCP session does not support call_tool")

                    tool_result = await _call_tool(session, tool_name, arguments)
                    logger.log(f"tool_result name={tool_name} output={tool_result}")

                    next_message = f"TOOL_RESULT {tool_name}: {tool_result}"

                else:
                    logger.log("Max iterations reached without FINAL_ANSWER")
    finally:
        logger.close()


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Keynote MCP client orchestrator")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="User query to seed the run")
    parser.add_argument("--max-iterations", type=int, default=8, help="Maximum agent iterations")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Gemini model to use")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])
    asyncio.run(run_agent(args.query, args.max_iterations, args.model))


if __name__ == "__main__":
    main()
