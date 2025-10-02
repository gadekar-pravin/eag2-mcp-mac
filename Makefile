.PHONY: setup run-client run-server-dev lint test

setup:
	python -m venv .venv
	. .venv/bin/activate && pip install -U pip && pip install -r requirements.txt

run-client:
	. .venv/bin/activate && python src/client/talk2mcp.py

run-server-dev:
	. .venv/bin/activate && python src/mcp_servers/mcp_server_keynote.py dev

# Bonus: Gmail MCP server
.PHONY: run-gmail-server-dev
run-gmail-server-dev:
	. .venv/bin/activate && python src/gmail_bonus/mcp_server_gmail.py dev


lint:
	. .venv/bin/activate && ruff check .

test:
	. .venv/bin/activate && pytest -q
