#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

command -v python3 >/dev/null 2>&1 || {
  echo "Thiếu python3. Hãy cài Python 3.11 trở lên rồi chạy lại."
  exit 1
}
command -v npm >/dev/null 2>&1 || {
  echo "Thiếu npm. Hãy cài Node.js 20.19 trở lên rồi chạy lại."
  exit 1
}

python3 -m venv .venv
"$ROOT_DIR/.venv/bin/python" -m pip install --upgrade pip
"$ROOT_DIR/.venv/bin/python" -m pip install -r webapp/requirements.txt pytest

npm install --prefix webapp/frontend
npm run build --prefix webapp/frontend

mkdir -p .data .secrets storage workspaces
echo "Cài đặt hoàn tất. Chạy: ./run-local.sh"
