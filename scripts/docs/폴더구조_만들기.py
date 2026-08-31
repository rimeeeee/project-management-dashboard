"""폴더 구조 문서 — 실제 폴더를 읽어 만듭니다."""
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP = {"node_modules",".git",".venv","__pycache__","dist",".pytest_cache","fonts"}
SKIP_FILE = {"package-lock.json",".DS_Store"}

NOTE = {
 "backend":"서버 (Python)",
 "backend/app/main.py":"서비스 시작점",
 "backend/app/core":"계산 규칙 ★",
 "backend/app/api":"화면이 호출하는 주소들",
 "backend/app/services":"조회·저장 처리",
 "backend/app/models":"데이터베이스 표 정의",
 "backend/app/collector":"공고 수집 ★",
 "backend/app/db":"데이터베이스 연결",
 "backend/alembic":"데이터베이스 구조 변경 이력",
 "backend/tests":"자동 테스트 63건",
 "backend/requirements.txt":"필요한 파이썬 라이브러리 목록",
 "frontend":"화면 (React)",
 "frontend/src/pages":"화면 단위",
 "frontend/src/components":"화면 구성 요소",
 "frontend/src/lib":"서버 통신·표시 변환",
 "frontend/src/styles":"디자인",
 "frontend/public":"이미지·글꼴 (그대로 배포됨)",
 "frontend/package.json":"필요한 프론트엔드 라이브러리 목록",
 "scripts":"운영·개발 도구",
 "scripts/set_password.py":"비밀번호 변경 ★배포 시 사용",
 "scripts/ntis_backfill.py":"NTIS 지난 공고 채우기",
 "scripts/seed":"개발용 예시 데이터 (서버에서 쓰지 않음)",
 "scripts/verify":"디자인 시안과 계산 규칙 대조 검증",
 "scripts/probe":"NTIS 응답 형식 조사 도구",
 "scripts/docs":"이 문서를 만드는 스크립트",
 "docs":"문서",
 "docs/prototype":"확정된 디자인 시안 (요구사항 원본)",
 "docs/ntis":"NTIS 응답 원문 (연동 근거 자료)",
 "data":"개발용 데이터베이스 (서버에서는 PostgreSQL 사용)",
 "Dockerfile":"서비스 이미지 만드는 설명서",
 "docker-compose.yml":"서비스 + 데이터베이스 실행 설정 ★배포 시 사용",
 ".env.example":"설정 항목 견본 ★배포 시 복사해서 사용",
 "README.md":"개발자용 안내",
}

lines=[]
def walk(d, prefix=""):
    items=sorted([p for p in d.iterdir()
                  if p.name not in SKIP and p.name not in SKIP_FILE and not p.name.startswith(".git")],
                 key=lambda p:(p.is_file(), p.name.lower()))
    for i,p in enumerate(items):
        last = i==len(items)-1
        rel=str(p.relative_to(ROOT))
        # 파일이 많은 폴더는 개수만 표시
        if p.is_dir() and rel in {"backend/tests","backend/alembic","frontend/src/pages",
                                  "frontend/src/components","frontend/src/lib","frontend/src/styles",
                                  "scripts/seed","scripts/verify","scripts/probe","scripts/docs",
                                  "docs/prototype","docs/ntis","frontend/public","backend/app/api",
                                  "backend/app/services","backend/app/models","backend/app/db"}:
            n=len([f for f in p.rglob("*") if f.is_file() and not any(s in f.parts for s in SKIP)])
            lines.append(f"{prefix}{'└── ' if last else '├── '}{p.name}/".ljust(38)+f"{NOTE.get(rel,'')}")
            continue
        lines.append(f"{prefix}{'└── ' if last else '├── '}{p.name}{'/' if p.is_dir() else ''}".ljust(38)+NOTE.get(rel,""))
        if p.is_dir():
            walk(p, prefix+("    " if last else "│   "))

walk(ROOT)

def loc(pattern, path):
    fs=[f for f in (ROOT/path).rglob(pattern) if not any(s in f.parts for s in SKIP)]
    return sum(len(f.read_text(encoding="utf-8",errors="ignore").splitlines()) for f in fs)

doc = f"""================================================================
 사업관리 대시보드 — 폴더 구조
 병원 디지털전략팀 / {datetime.date.today()}
================================================================


┌──────────────────────────────────────────────────────────────┐
│ 크게 보면 4덩어리입니다                                       │
└──────────────────────────────────────────────────────────────┘

  backend/    서버      — 자료를 저장하고 계산하고 공고를 수집
  frontend/   화면      — 사용자가 보는 부분
  scripts/    도구      — 비밀번호 변경 등 운영에 쓰는 것
  docs/       문서      — 지금 보시는 것 포함

  나머지 파일은 대부분 설정 파일입니다.


┌──────────────────────────────────────────────────────────────┐
│ 배포할 때 보실 파일은 3개뿐입니다                             │
└──────────────────────────────────────────────────────────────┘

  .env.example          설정 견본 — .env 로 복사해서 값을 채웁니다
  docker-compose.yml    이걸로 실행합니다 (docker compose up -d --build)
  scripts/set_password.py   비밀번호를 정합니다

  자세한 순서는 docs/기술스택.txt 의 '배포 방법' 을 보세요.


================================================================
 전체 구조
================================================================

""" + "\n".join(lines) + f"""


  ※ 아래는 프로그램이 자동으로 만드는 것이라 제외했습니다.
     node_modules/  .venv/  dist/  __pycache__/  글꼴파일 376개


================================================================
 규모
================================================================

  서버 (Python)        {loc('*.py','backend/app'):>6,} 줄
  화면 (TypeScript)    {loc('*.tsx','frontend/src')+loc('*.ts','frontend/src'):>6,} 줄
  디자인 (CSS)         {loc('*.css','frontend/src/styles'):>6,} 줄
  자동 테스트          {loc('*.py','backend/tests'):>6,} 줄


================================================================
 유지보수하실 분께 (★ 표시한 곳)
================================================================

 1. backend/app/core/
    진행률·상태 판정·보고 회차 계산이 모두 여기 있습니다.
    화면은 계산하지 않고 서버가 준 값을 보여주기만 합니다.
    계산 규칙을 고칠 일이 있으면 여기만 보시면 됩니다.

 2. backend/app/collector/
    공고 수집입니다. 그중 fetch.py 의 '응답 잘림 대응' 은
    한국보건복지인재원 서버가 응답을 중간에 끊는 문제에 대한 것입니다.
    지우면 수집 건수가 실행할 때마다 달라집니다.

 3. frontend/src/styles/prototype.css
    확정된 디자인 시안에서 그대로 가져온 파일입니다. 수정하지 마세요.
    바꿀 일이 있으면 같은 폴더의 overrides.css 에 적습니다.
    그래야 '무엇을 왜 바꿨는지' 가 한 곳에 모입니다.

 4. scripts/verify/run.py
    지금 코드가 디자인 시안과 같은 값을 내는지 자동으로 대조합니다.
    계산 규칙을 고쳤다면 반드시 돌려 보세요.

       python scripts/verify/run.py
"""

out = ROOT/"docs"/"폴더구조.txt"
out.write_text(doc, encoding="utf-8")
print(f"만들었습니다 ({len(doc.splitlines())}줄)")
