#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
  echo "Chưa có môi trường Python. Hãy chạy ./setup.sh trước."
  exit 1
fi
if [[ ! -f "$ROOT_DIR/webapp/frontend/dist/index.html" ]]; then
  echo "Chưa có frontend build. Hãy chạy ./setup.sh trước."
  exit 1
fi

mkdir -p .data .secrets storage workspaces
KEY_FILE="$ROOT_DIR/.secrets/master.key"
if [[ ! -s "$KEY_FILE" ]]; then
  umask 077
  python3 -c 'import secrets; print(secrets.token_hex(32))' > "$KEY_FILE"
fi

export NOVELKIT_DATABASE_URL="${NOVELKIT_DATABASE_URL:-sqlite:///$ROOT_DIR/.data/novelkit-lite.db}"
export NOVELKIT_STORAGE_ROOT="${NOVELKIT_STORAGE_ROOT:-$ROOT_DIR/storage}"
export NOVELKIT_WORKSPACE_ROOT="${NOVELKIT_WORKSPACE_ROOT:-$ROOT_DIR/workspaces}"
export NOVELKIT_SECRETS_DIR="${NOVELKIT_SECRETS_DIR:-$ROOT_DIR/.secrets}"
export NOVELKIT_SECRETS_KEY="${NOVELKIT_SECRETS_KEY:-$(<"$KEY_FILE")}"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

echo "NovelKit V2-lite đang chạy tại http://$HOST:$PORT"
exec "$ROOT_DIR/.venv/bin/python" -m uvicorn webapp.api.main:app --host "$HOST" --port "$PORT"
