#!/usr/bin/env bash
# 개발용 — 백엔드(8000)와 프론트엔드(5173)를 함께 띄웁니다.
# 화면은 http://localhost:5173 에서 봅니다.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env 파일이 없어 .env.example 을 복사해 만들었습니다."
fi

# 파이썬 위치는 운영체제마다 다릅니다 (Windows 는 .venv/Scripts/python.exe)
PY="$PWD/.venv/bin/python"
[ -x "$PY" ] || PY="$PWD/.venv/Scripts/python.exe"
if [ ! -x "$PY" ]; then
  echo ".venv 가 없습니다. docs/개발.md 의 '개발 환경 준비' 를 먼저 해 주세요." >&2
  exit 1
fi

trap 'kill 0' EXIT
( cd backend && "$PY" -m uvicorn app.main:app --reload --port 8000 ) &
( cd frontend && npm run dev ) &
wait
