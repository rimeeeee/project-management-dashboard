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
설정하지 않으면 개발용 기본 비밀번호(`bizdash2026`)로 동작하며 서버 로그에
경고가 남습니다.

### 로그인 화면으로 돌아가기

한 번 로그인하면 쿠키가 12시간(‘로그인 유지’ 를 켰으면 30일) 남아 있어서,
새로고침해도 로그인 화면이 다시 나오지 않습니다. 화면에 로그아웃 버튼을 두지
않기로 했으므로, 주소 뒤에 `?logout` 을 붙이면 됩니다.

    http://localhost:5173/?logout

로그인 화면을 확인해야 할 때, 그리고 여럿이 쓰는 PC 에서 자리를 뜰 때 씁니다.

## 배포

배포 환경이 정해지면 `.env` 를 채우고:

```bash
docker compose up -d --build
```

`docker-compose.yml` 은 아직 실행해 검증하지 못했습니다 (아래 참고).

## 테스트

```bash
cd backend && ../.venv/bin/python -m pytest      # 저장·충돌·이력
.venv/bin/python scripts/verify/run.py           # 프로토타입 대조
```

## 실제 서버에 올릴 때

새 서버에서는 데이터베이스가 비어 있는 상태로 시작합니다.
**`scripts/seed/load_seed.py` 는 돌리지 마세요.** 프로토타입 예시 사업이 들어갑니다.

```bash
# 1) 설정값 준비
cp .env.example .env
.venv/bin/python scripts/set_password.py     # 비밀번호 정하기
# .env 에서 SECRET_KEY 를 바꾸고, https 라면 COOKIE_SECURE=true

# 2) 띄우기
docker compose up -d --build                 # 표는 자동으로 만들어집니다

# 3) 화면에서
#    로그인 → [사업 현황 (공고)] → [지금 수집]  (공고 300건 이상 들어옵니다)
#    → [신규 사업 등록] 으로 실제 사업 등록
```

지난 공고까지 채우려면 (선택):

```bash
.venv/bin/python scripts/ntis_backfill.py --days 180
```

예시 사업이 실수로 들어갔다면:

```bash
.venv/bin/python scripts/seed/clear_examples.py
```

## 문서

| | |
|---|---|
| [docs/설치방법.txt](docs/설치방법.txt) | **이 폴더를 처음 받았을 때 — 설치 5단계** |
| [docs/폴더구조.txt](docs/폴더구조.txt) | 전체 폴더 구조 |
| [docs/기술스택.txt](docs/기술스택.txt) | 쓰인 기술과 버전 |
| [docs/공고수집.md](docs/공고수집.md) | 수집 구조 · NTIS 옵션 실측 결과 |

폴더구조.txt 는 실제 폴더를 읽어 만듭니다. 파일을 추가했다면 다시 만들어 주세요.

```bash
.venv/bin/python scripts/docs/폴더구조_만들기.py
```

## 알아둘 것

- **글꼴은 저장소에 들어 있습니다** (`frontend/public/fonts/`, 376조각).
  시안은 Google Fonts CDN 을 썼지만, 병원 내부망에서 막히면 다른 글꼴로
  떨어져 글자 크기·굵기가 달라 보입니다. 다시 받으려면
  `.venv/bin/python scripts/fetch_fonts.py`. 화면을 띄웠을 때 바깥으로 나가는
  요청이 0건인 것을 확인했습니다.

- **날짜 판정은 한국 시간(Asia/Seoul) 고정입니다.** 사업 진척률과 공고 마감 판정이
  모두 '오늘'에 걸려 있어서, 서버가 UTC 로 돌면 밤 9시부터 다음 날로 판정됩니다.
- **금액은 원 단위 정수로 저장합니다.** 억 환산은 화면에 표시할 때만 합니다.
- **화면 스타일(`frontend/src/styles/prototype.css`)은 프로토타입에서 그대로 복사한
  것입니다.** 글씨 크기(16.8px, 17.4px 등 소수점 포함)와 색은 실무 검토를 거쳐
  확정된 값이라 임의로 고치면 안 됩니다.
- **저장은 회차 한 줄만 건드립니다.** 두 사람이 같은 회차를 동시에 고치면
  조용히 덮어쓰지 않고, 다른 사람이 먼저 저장했다고 알려 준 뒤 사람이 정하게 합니다.
- **입력자·수정시각은 화면에 표시하지 않습니다.** 비밀번호 하나로 들어오는
  구조라 누가 입력했는지 구분할 방법이 없기 때문입니다. 나중에 사내 계정을
  붙이면 그때 함께 붙이면 됩니다.
- **입력 내역이 있는 사업은 보고 주기를 바꿀 수 없습니다.** 회차 키(W…/B…/M…)가
  이미 저장되어 있어서, 주기가 바뀌면 기존 회차가 다른 기간을 가리킵니다.
  격주 사업은 회차 키가 시작일 기준이라 시작일도 함께 잠깁니다.

## 진행 상황

- [x] 1단계 — 프로젝트 뼈대, 비밀번호 게이트
- [ ] 2단계 — 데이터베이스 스키마, 프로토타입 시드 데이터 이관
- [ ] 3단계 — 조회 API + 화면 이식 (읽기 전용)
- [x] 4단계 — 회차별 저장, 입력자·수정시각, 동시 저장 충돌 처리
- [x] 5단계 — 사업 등록·수정·삭제
- [x] 6단계 — 공고 화면(페이징) + 수집기 서버 이식 + 스케줄러
- [x] 7단계 — NTIS 통합공고 연동
