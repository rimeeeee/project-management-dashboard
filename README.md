# 사업관리 대시보드

병원 디지털전략팀 사업관리 대시보드. 프로토타입(`사업관리_대시보드_4.html`)을
여러 명이 함께 쓸 수 있는 웹 서비스로 옮기는 작업입니다.

## 구성

| | |
|---|---|
| 백엔드 | FastAPI (Python) |
| 프론트엔드 | React + TypeScript (Vite) |
| 데이터베이스 | PostgreSQL (운영) / SQLite (로컬) |
| 공고 수집 | 백엔드 안에서 APScheduler 로 주 2회 실행 |

## 처음 준비

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
cp .env.example .env
```

## 개발 중 실행

```bash
./scripts/dev.sh
```

화면은 http://localhost:5173 에서 봅니다. `/api` 요청은 백엔드(8000)로 넘어갑니다.

## 로그인 비밀번호

담당자 계정은 두지 않고 비밀번호 하나로 들어갑니다.

```bash
.venv/bin/python scripts/set_password.py
```

`.env` 의 `APP_PASSWORD_HASH` 에 해시만 저장되고 비밀번호 자체는 남지 않습니다.
설정하지 않으면 개발용 기본 비밀번호(`bizdash2026`)로 동작하며, 서버 로그와
화면 위에 경고가 뜹니다.

## 배포

배포 환경이 정해지면 `.env` 를 채우고:

```bash
docker compose up -d --build
```

`docker-compose.yml` 은 아직 실행해 검증하지 못했습니다 (아래 참고).

## 알아둘 것

- **날짜 판정은 한국 시간(Asia/Seoul) 고정입니다.** 사업 진척률과 공고 마감 판정이
  모두 '오늘'에 걸려 있어서, 서버가 UTC 로 돌면 밤 9시부터 다음 날로 판정됩니다.
- **금액은 원 단위 정수로 저장합니다.** 억 환산은 화면에 표시할 때만 합니다.
- **화면 스타일(`frontend/src/styles/prototype.css`)은 프로토타입에서 그대로 복사한
  것입니다.** 글씨 크기(16.8px, 17.4px 등 소수점 포함)와 색은 실무 검토를 거쳐
  확정된 값이라 임의로 고치면 안 됩니다.

## 진행 상황

- [x] 1단계 — 프로젝트 뼈대, 비밀번호 게이트
- [ ] 2단계 — 데이터베이스 스키마, 프로토타입 시드 데이터 이관
- [ ] 3단계 — 조회 API + 화면 이식 (읽기 전용)
- [ ] 4단계 — 회차별 저장, 입력자·수정시각, 동시 저장 충돌 처리
- [ ] 5단계 — 사업 등록·수정·삭제
- [ ] 6단계 — 공고 화면(페이징) + 수집기 서버 이식 + 스케줄러
- [ ] 7단계 — NTIS 통합공고 연동
