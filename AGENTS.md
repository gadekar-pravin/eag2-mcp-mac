# Repository Guidelines

## Project Structure & Module Organization
`src/client` hosts the Gemini-driven orchestrator and prompt helpers; treat it as the entry point. `src/mcp_servers` contains the FastMCP server, with AppleScripts under `src/mcp_servers/applescript` and shared utilities in `src/mcp_servers/utils`. Keep Python wrappers and AppleScript updates together so automation stays in sync. Tests live in `tests` (protocol, server contracts, and AppleScript smoke checks), documentation sits in `docs`, run artifacts accumulate in `logs`, and reusable shell helpers stay in `scripts`.

## Build, Test, and Development Commands
- `make setup` – create `.venv` and install dependencies from `requirements.txt`.
- `make run-client` – run `src/client/talk2mcp.py` against the configured MCP server.
- `make run-server-dev` – start the Keynote server locally for interactive debugging.
- `make lint` – execute Ruff; fix reported style or import issues before pushing.
- `make test` – call `pytest -q`; use `pytest tests/test_protocol.py -k FUNCTION_CALL` for focused runs.

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indentation, snake_case names, and descriptive module paths. The codebase favors type hints, dataclasses, and f-strings—extend those patterns when adding logic. Keep AppleScript files small, action-oriented, and named like `draw_rectangle.applescript`. Run `make lint` before reviews; Ruff enforces formatting, import order, and lightweight complexity limits.

## Testing Guidelines
Pytest powers verification, so every new tool branch or parser path should have a companion test in `tests`. Name files `test_<feature>.py` and test functions `test_<behavior>` to match existing discovery rules. Expand `test_server_contracts.py` with patched runners for AppleScript changes, and document fixtures in `tests/conftest.py` when introducing new dependencies.

## Commit & Pull Request Guidelines
Write commits in the imperative mood with optional scope prefixes (e.g., `client: log tool schema`) and keep subject lines ≤72 characters. Describe motivation, side effects, and testing in the body when relevant. PRs should summarize changes, list verification steps (`make run-client`, `make test`), link issues or specs, and attach screenshots when Keynote output changes. Flag follow-up work explicitly instead of leaving TODOs in code.

## Security & Configuration Tips
Copy `.env.example` to `.env`, set `GEMINI_API_KEY`, and avoid committing secrets. Grant macOS Accessibility and Automation permissions to the shell or IDE driving the scripts before testing. Treat `logs/agent.log` as sensitive; rotate API keys if the log captures credentials, and trim shared demos to the run identifier emitted by the client logger.
