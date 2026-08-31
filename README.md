# 사업관리 대시보드

디지털전략팀에서 쓰는 사업관리 대시보드입니다.
사업별 진척·예산 집행을 회차마다 기록하고, 기관 4곳의 사업 공고를 모아 봅니다.

| | |
|---|---|
| 백엔드 | FastAPI (Python) |
| 프론트엔드 | React + TypeScript (Vite) |
| 데이터베이스 | PostgreSQL 16 (운영) · SQLite (개발 PC) |
| 공고 수집 | 화면의 [지금 수집] 버튼으로 실행 |

**설치하려면 [docs/설치방법.txt](docs/설치방법.txt) 를 보세요.**
아래는 개발할 때 필요한 내용입니다.

## 개발 환경 준비

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd frontend && npm install && cd ..
cp .env.example .env
.venv/bin/python scripts/set_password.py
```

## 실행

```bash
./scripts/dev.sh                                  # macOS · Linux
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1   # Windows
```

화면은 http://localhost:5173 에서 봅니다. `/api` 요청은 백엔드(8000)로 넘어갑니다.

한 번 로그인하면 쿠키가 12시간 남아 로그인 화면이 다시 나오지 않습니다.
로그인 화면을 보려면 주소 뒤에 `?logout` 을 붙입니다.

## 테스트

```bash
cd backend && ../.venv/bin/python -m pytest      # 저장·충돌·이력·보안
.venv/bin/python scripts/verify/run.py           # 디자인 시안 대조
```

## 손대면 안 되는 곳

- **`backend/app/core/`** — 진행률·상태 판정·회차 계산이 모두 여기 있습니다.
  화면은 계산하지 않고 서버가 준 값을 표시만 합니다. 규칙이 두 군데 있으면
  한쪽만 고쳐져 숫자가 어긋납니다.

- **`frontend/src/styles/prototype.css`** — 확정된 디자인 시안에서 그대로
  복사한 파일입니다. 글씨 크기(16.8px 등 소수점 포함)와 색은 실무 검토를 거친
  값입니다. 바꿀 일이 있으면 같은 폴더의 `overrides.css` 에 적습니다.

- **`backend/app/collector/fetch.py` 의 응답 잘림 대응** — 한국보건복지인재원
  서버가 응답을 중간에 끊습니다. 지우면 수집 건수가 실행할 때마다 달라집니다.

- **`docs/prototype/`** — 요구사항 원본입니다. `scripts/verify/run.py` 가
  이 파일을 실행해 지금 코드와 대조합니다.

## 규칙

- **날짜는 한국 시간(Asia/Seoul) 기준입니다.** 진척률과 공고 마감 판정이
  모두 '오늘'에 걸려 있습니다.
- **금액은 원 단위 정수로 저장합니다.** 억 환산은 화면에 표시할 때만 합니다.
- **저장은 회차 한 줄만 건드립니다.** 두 사람이 같은 회차를 동시에 고치면
  조용히 덮어쓰지 않고, 먼저 저장한 사람이 있다고 알린 뒤 사람이 정합니다.
- **입력 내역이 있는 사업은 보고 주기를 바꿀 수 없습니다.** 회차 키(W…/B…/M…)가
  이미 저장되어 있어 주기가 바뀌면 기존 회차가 다른 기간을 가리킵니다.
  격주 사업은 회차 키가 시작일 기준이라 시작일도 함께 잠깁니다.
- **글꼴은 저장소에 들어 있습니다** (`frontend/public/fonts/`).
  시안은 Google Fonts CDN 을 썼지만 내부망에서 막히면 글자가 달라 보입니다.
  다시 받으려면 `.venv/bin/python scripts/fetch_fonts.py`.

## 도구

```bash
scripts/set_password.py         로그인 비밀번호 변경
scripts/ntis_backfill.py        NTIS 지난 공고 채우기 (--days 180)
scripts/make_package.sh         서버에 올릴 파일만 모아 압축
scripts/seed/load_seed.py       개발용 예시 자료 넣기 (서버에서 쓰지 마세요)
scripts/seed/clear_examples.py  예시 자료 지우기
scripts/docs/폴더구조_만들기.py  docs/폴더구조.txt 다시 만들기
```

## 문서

| | |
|---|---|
| [docs/설치방법.txt](docs/설치방법.txt) | 폴더를 처음 받았을 때 — 설치 5단계 |
| [docs/기술스택.txt](docs/기술스택.txt) | 쓰인 기술과 버전 |
| [docs/폴더구조.txt](docs/폴더구조.txt) | 폴더별 설명 |
| [docs/공고수집.md](docs/공고수집.md) | 수집 구조 · NTIS 옵션 실측 결과 |
