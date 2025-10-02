#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -d "${ROOT_DIR}/.venv" ]]; then
  echo "error: virtual environment not found at ${ROOT_DIR}/.venv" >&2
  echo "run 'make setup' first" >&2
  exit 1
fi

source "${ROOT_DIR}/.venv/bin/activate"
python "${ROOT_DIR}/src/client/talk2mcp.py" "$@"
