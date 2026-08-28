#!/usr/bin/env bash
# 개발용 — 백엔드(8000)와 프론트엔드(5173)를 함께 띄웁니다.
# 화면은 http://localhost:5173 에서 봅니다.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env 파일이 없어 .env.example 을 복사해 만들었습니다."
fi

trap 'kill 0' EXIT
( cd backend && ../.venv/bin/python -m uvicorn app.main:app --reload --port 8000 ) &
( cd frontend && npm run dev ) &
wait
