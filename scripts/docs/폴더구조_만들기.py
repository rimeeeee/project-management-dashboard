"""폴더 구조 문서를 실제 파일에서 생성합니다 (손으로 적지 않아 틀릴 여지가 없습니다)."""
import subprocess, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {"node_modules", ".git", ".venv", "__pycache__", "dist", ".pytest_cache", "fonts"}

# 각 항목에 붙일 설명
NOTE = {
 "README.md":"전체 안내 · 실행 방법",
 "docker-compose.yml":"PostgreSQL + 백엔드 한 번에 띄우기",
 "Dockerfile":"백엔드 이미지",
 ".env":"실제 설정값 (git 에 올리지 않음)",
 ".env.example":"설정 항목 見本 — 새 서버에서 복사해 채웁니다",
 "backend":"FastAPI 서버",
 "backend/app/main.py":"앱 시작 · 라우터 등록 · 스케줄러",
 "backend/app/core":"★ 규칙이 사는 곳 (여기만 고치면 전체에 반영)",
 "backend/app/core/calc.py":"진행률 · 상태 판정 (−5%p / −15%p)",
 "backend/app/core/periods.py":"보고 회차 계산 (주간/격주/월간)",
 "backend/app/core/config.py":"설정값 읽기",
 "backend/app/core/security.py":"비밀번호(Argon2) · 세션 쿠키",
 "backend/app/core/timeutil.py":"한국시간 변환 (SQLite 시간대 대응)",
 "backend/app/core/http.py":"SSL 인증서 (수집이 실패하던 원인)",
 "backend/app/models":"데이터베이스 표 14개",
 "backend/app/services":"조회 · 저장 로직",
 "backend/app/api":"HTTP 창구",
 "backend/app/db":"데이터베이스 연결",
 "backend/app/collector":"★ 공고 수집",
 "backend/app/collector/fetch.py":"받아오기 (인재원 응답 잘림 대응 — 지우지 마세요)",
 "backend/app/collector/parse.py":"제목·게시일·마감일 읽기 (원본 검증 로직)",
 "backend/app/collector/sources.py":"기관 3곳 + NTIS",
 "backend/app/collector/runner.py":"수집 실행 · 데이터베이스 반영",
 "backend/app/collector/scheduler.py":"자동 수집 (기본 꺼짐)",
 "backend/alembic":"데이터베이스 변경 이력",
 "backend/tests":"자동 테스트 63건",
 "frontend":"React + TypeScript 화면",
 "frontend/src/App.tsx":"로그인 여부 판단 · ?logout",
 "frontend/src/pages":"화면",
 "frontend/src/components":"화면 조각",
 "frontend/src/lib":"서버 통신 · 표시 변환",
 "frontend/src/styles":"스타일",
 "frontend/src/styles/prototype.css":"★ 프로토타입에서 그대로 복사 — 손대지 마세요",
 "frontend/src/styles/overrides.css":"★ 일부러 바꾼 것만 (무엇을 왜 바꿨는지 주석에)",
 "frontend/public/brand":"로고",
 "frontend/public/prototype.html":"프로토타입 (나란히 비교용)",
 "scripts":"운영 · 개발 도구",
 "scripts/set_password.py":"비밀번호 변경",
 "scripts/ntis_backfill.py":"NTIS 지난 공고 채우기",
 "scripts/fetch_fonts.py":"글꼴 내려받기",
 "scripts/dev.sh":"개발 서버 실행",
 "scripts/seed":"프로토타입 데이터 이관",
 "scripts/verify":"★ 프로토타입 대조 검증 (회차 2,700건)",
 "scripts/probe":"NTIS 필드 조사용",
 "docs":"문서",
 "docs/prototype":"★ 원본 HTML + 수집 스크립트 = 요구사항 명세서",
 "docs/ntis":"NTIS 응답 원문 (매핑 근거)",
 "data":"로컬 SQLite (git 에 올리지 않음)",
}

lines = []
def walk(d: Path, prefix=""):
    items = sorted([p for p in d.iterdir() if p.name not in SKIP_DIRS and not p.name.startswith(".git")],
                   key=lambda p: (p.is_file(), p.name.lower()))
    items = [p for p in items if p.name not in {"package-lock.json"}]
    for i, p in enumerate(items):
        last = (i == len(items) - 1)
        branch = "└── " if last else "├── "
        rel = str(p.relative_to(ROOT))
        note = NOTE.get(rel, "")
        name = p.name + ("/" if p.is_dir() else "")
        line = f"{prefix}{branch}{name}"
        if note:
            line = f"{line:<46}{note}"
        lines.append(line)
        if p.is_dir():
            walk(p, prefix + ("    " if last else "│   "))

walk(ROOT)

def count(pattern, path):
    try:
        files = list((ROOT / path).rglob(pattern))
        files = [f for f in files if not any(s in f.parts for s in SKIP_DIRS)]
        return sum(len(f.read_text(encoding="utf-8", errors="ignore").splitlines()) for f in files)
    except Exception:
        return 0

header = f"""사업관리 대시보드 — 폴더 구조
================================================================
만든 날짜: {datetime.date.today()}
이 파일은 scripts 로 실제 폴더를 읽어 만든 것입니다.

아래는 제외했습니다 (프로그램이 자동으로 만드는 것들):
  node_modules/   프론트엔드 라이브러리
  .venv/          파이썬 라이브러리
  dist/           빌드 결과물
  __pycache__/    파이썬 임시 파일
  frontend/public/fonts/   글꼴 파일 376개
  package-lock.json

★ 표시는 특히 중요한 곳입니다.
================================================================

"""

footer = f"""

================================================================
코드 규모
================================================================
  백엔드 (파이썬)      {count('*.py','backend/app'):>6,} 줄
  자동 테스트          {count('*.py','backend/tests'):>6,} 줄
  프론트엔드 (TS/TSX)  {count('*.tsx','frontend/src')+count('*.ts','frontend/src'):>6,} 줄
  스타일 (CSS)         {count('*.css','frontend/src/styles'):>6,} 줄

================================================================
꼭 알아두실 것
================================================================
1. backend/app/core/ 가 규칙의 유일한 자리입니다.
   진행률·상태 판정·회차 계산이 전부 여기 있습니다.
   화면은 서버가 계산한 값을 받아 표시만 합니다.
   규칙이 두 군데 있으면 한쪽만 고쳐져 숫자가 어긋나기 때문입니다.

2. frontend/src/styles/prototype.css 는 손대지 마세요.
   프로토타입에서 그대로 복사한 파일입니다.
   바꿀 일이 있으면 overrides.css 에 적습니다.
   그래야 "무엇을 왜 바꿨는지" 가 한 파일에 모입니다.

3. docs/prototype/ 이 요구사항 명세서입니다.
   scripts/verify/run.py 가 이 원본을 실행해 지금 코드와 대조합니다.
   계산 규칙을 고쳤다면 반드시 다시 돌려 보세요.

4. backend/app/collector/fetch.py 의 응답 잘림 대응은 지우지 마세요.
   한국보건복지인재원 서버가 응답을 중간에 끊습니다.
   이 대응이 없으면 수집 건수가 실행할 때마다 들쭉날쭉해집니다.
"""

out = ROOT / "docs" / "폴더구조.txt"
out.write_text(header + "\n".join(lines) + footer, encoding="utf-8")
print(f"만들었습니다: {out.relative_to(ROOT)}  ({len(lines)}줄)")
