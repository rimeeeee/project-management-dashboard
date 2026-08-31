#!/usr/bin/env bash
# 서버에 올릴 파일만 모아 패키지를 만듭니다.
#
#   bash scripts/make_package.sh
#   → bizdash-배포.tar.gz  (이 파일 하나만 서버로 옮기면 됩니다)
#
# 문서·시안·테스트·개발 도구는 넣지 않습니다.

set -e
cd "$(dirname "$0")/.."
OUT="bizdash-배포"

echo "1) 화면 빌드"
(cd frontend && npm ci --silent && npm run build)

echo "2) 파일 모으기"
rm -rf "$OUT" "$OUT.tar.gz"
mkdir -p "$OUT/frontend" "$OUT/scripts"

cp -r backend "$OUT/"
rm -rf "$OUT/backend/tests" "$OUT/backend/.pytest_cache"

cp -r frontend/dist "$OUT/frontend/"

cp scripts/set_password.py    "$OUT/scripts/"      # 비밀번호 정하기
cp scripts/ntis_backfill.py   "$OUT/scripts/"      # 지난 공고 채우기(선택)
cp .env.example               "$OUT/"

find "$OUT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$OUT" -name "*.pyc" -delete 2>/dev/null || true

tar -czf "$OUT.tar.gz" "$OUT"
rm -rf "$OUT"

echo
echo "완성: $OUT.tar.gz  ($(du -h "$OUT.tar.gz" | cut -f1))"
echo "이 파일 하나를 서버로 옮기고 docs/기술스택.txt 의 설치 방법을 따르세요."
