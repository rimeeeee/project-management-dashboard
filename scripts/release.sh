#!/usr/bin/env bash
# 서버에 올릴 준비를 합니다. (macOS · Linux)
#
#   bash scripts/release.sh
#
# 하는 일
#   1. 백엔드 테스트
#   2. 디자인 시안 대조
#   3. 화면 빌드 (frontend/dist)
#   4. 바뀐 화면을 커밋 대상에 올려 둠
#
# 화면 빌드를 깜빡하고 커밋하면 서버가 새 코드에 옛날 화면을 쓰게 됩니다.
# 그 일이 없도록 한 번에 묶어 둔 것입니다.
# Windows 에서는 scripts/release.ps1 을 쓰세요. 하는 일은 같습니다.
set -euo pipefail
cd "$(dirname "$0")/.."

PY="$PWD/.venv/bin/python"
[ -x "$PY" ] || PY="$PWD/.venv/Scripts/python.exe"   # Windows(Git Bash)
if [ ! -x "$PY" ]; then
  echo ".venv 가 없습니다. docs/개발.md 의 '개발 환경 준비' 를 먼저 해 주세요." >&2
  exit 1
fi

export PYTHONUTF8=1

echo
echo "[1/4] 백엔드 테스트"
( cd backend && "$PY" -m pytest -q )

echo
echo "[2/4] 디자인 시안 대조"
"$PY" scripts/verify/run.py

echo
echo "[3/4] 화면 빌드"
cd frontend
# 항상 비운 자리에 새로 만듭니다. 두 가지 이유가 있습니다.
#   · 개발 서버가 남긴 캐시나 지난 결과물이 빌드를 방해하는 일이 있습니다
#   · dist 를 git 에 넣으므로, 지난 빌드 찌꺼기가 남으면 그대로 서버까지 갑니다
rm -rf node_modules/.vite dist
npm run build
cd ..

echo
echo "[4/4] 바뀐 화면을 커밋 대상에 올립니다"
git add frontend/dist

cat <<'MSG'

준비가 끝났습니다. 이제 커밋하고 올리세요.

    git add -A
    git commit -m "무엇을 고쳤는지"
    git push

서버에서는 git pull 후 서비스만 다시 시작하면 됩니다.
(표 구조를 바꿨다면 서버에서 alembic upgrade head 도 함께)
MSG
