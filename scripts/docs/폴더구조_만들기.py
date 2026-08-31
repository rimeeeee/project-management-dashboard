"""
docs/폴더구조.txt 를 실제 폴더를 읽어 만듭니다.

    .venv/bin/python scripts/docs/폴더구조_만들기.py

파일을 추가하거나 옮긴 뒤에 돌려 주세요.
폴더 설명을 붙이려면 아래 NOTE 에 한 줄 추가하면 됩니다.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP = {"node_modules", ".git", ".venv", "__pycache__", "dist", ".pytest_cache", "fonts"}
SKIP_FILE = {"package-lock.json", ".DS_Store", "tsconfig.tsbuildinfo",
             "Dockerfile", "docker-compose.yml", ".env"}

# 파일까지 펼치지 않고 폴더 한 줄로만 보여 줄 곳
FOLD = {"backend/tests", "backend/alembic", "backend/app/api", "backend/app/db",
        "backend/app/models", "backend/app/services", "backend/app/core",
        "backend/app/collector", "frontend/src/pages", "frontend/src/components",
        "frontend/src/lib", "frontend/src/styles", "frontend/public",
        "scripts/seed", "scripts/verify", "scripts/probe", "scripts/docs",
        "docs/prototype", "docs/ntis", "data"}

NOTE = {
 "backend": "서버 (Python)",
 "backend/app/main.py": "서비스 시작점",
 "backend/app/core": "계산 규칙 ★",
 "backend/app/api": "화면이 호출하는 주소",
 "backend/app/services": "조회·저장 처리",
 "backend/app/models": "표 정의",
 "backend/app/collector": "공고 수집 ★",
 "backend/app/db": "데이터베이스 연결",
 "backend/alembic": "표 구조 변경 이력",
 "backend/tests": "자동 테스트",
 "backend/requirements.txt": "설치할 파이썬 라이브러리",
 "frontend": "화면 (React)",
 "frontend/src/pages": "화면 단위",
 "frontend/src/components": "화면 구성 요소",
 "frontend/src/lib": "서버 통신·표시 변환",
 "frontend/src/styles": "디자인 ★",
 "frontend/public": "로고·글꼴",
 "frontend/package.json": "설치할 프론트엔드 라이브러리",
 "scripts": "도구",
 "scripts/set_password.py": "비밀번호 변경",
 "scripts/ntis_backfill.py": "NTIS 지난 공고 채우기",
 "scripts/make_package.sh": "서버에 올릴 파일만 모아 압축",
 "scripts/fetch_fonts.py": "글꼴 내려받기",
 "scripts/dev.sh": "개발 서버 실행",
 "scripts/seed": "개발용 예시 자료",
 "scripts/verify": "디자인 시안 대조 검증 ★",
 "scripts/probe": "NTIS 응답 형식 조사",
 "scripts/docs": "이 문서를 만드는 스크립트",
 "docs": "문서",
 "docs/prototype": "확정된 디자인 시안 (요구사항 원본)",
 "docs/ntis": "NTIS 응답 원문",
 "data": "자료 저장 (bizdash.db)",
 ".env.example": "설정 견본 — .env 로 복사해서 씁니다",
 "README.md": "개발자용 안내",
}

lines = []


def walk(d: Path, prefix: str = "") -> None:
    items = sorted(
        [p for p in d.iterdir()
         if p.name not in SKIP and p.name not in SKIP_FILE and not p.name.startswith(".git")],
        key=lambda p: (p.is_file(), p.name.lower()),
    )
    for i, p in enumerate(items):
        last = i == len(items) - 1
        rel = str(p.relative_to(ROOT))
        name = p.name + ("/" if p.is_dir() else "")
        row = f"{prefix}{'└── ' if last else '├── '}{name}"
        note = NOTE.get(rel, "")
        lines.append(f"{row:<36}{note}".rstrip())
        if p.is_dir() and rel not in FOLD:
            walk(p, prefix + ("    " if last else "│   "))


walk(ROOT)


def loc(pattern: str, path: str, exclude: set[str] = frozenset()) -> int:
    fs = [f for f in (ROOT / path).rglob(pattern)
          if not any(s in f.parts for s in SKIP) and f.name not in exclude]
    return sum(len(f.read_text(encoding="utf-8", errors="ignore").splitlines()) for f in fs)


def tests() -> int:
    """테스트 개수 — 파일에서 직접 셉니다."""
    n = 0
    for f in (ROOT / "backend" / "tests").rglob("test_*.py"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("def test_"):
                n += 1
            if line.startswith("@pytest.mark.parametrize"):
                n += 6   # 대략치
    return n


doc = f"""================================================================
 사업관리 대시보드 — 폴더 구조
================================================================

""" + "\n".join(lines) + f"""


  ※ 아래는 프로그램이 만드는 것이라 목록에서 뺐습니다.
     node_modules/  .venv/  frontend/dist/  __pycache__/  글꼴 376개


────────────────────────────────────────────────────────────────
 규모
────────────────────────────────────────────────────────────────

  서버 (Python)        {loc('*.py','backend/app'):>6,} 줄
  화면 (TypeScript)    {loc('*.tsx','frontend/src')+loc('*.ts','frontend/src'):>6,} 줄
  디자인 (CSS)         {loc('*.css','frontend/src/styles', {'fonts.css'}):>6,} 줄
  자동 테스트          {loc('*.py','backend/tests'):>6,} 줄


────────────────────────────────────────────────────────────────
 고칠 일이 있을 때 (★ 표시한 곳)
────────────────────────────────────────────────────────────────

 backend/app/core/
   진행률·상태 판정·보고 회차 계산이 모두 여기 있습니다.
   화면은 계산하지 않고 서버가 준 값을 보여주기만 합니다.

 backend/app/collector/
   공고 수집입니다. fetch.py 의 '응답 잘림 대응' 은 한국보건복지인재원
   서버가 응답을 중간에 끊는 문제에 대한 것입니다.
   지우면 수집 건수가 실행할 때마다 달라집니다.

 frontend/src/styles/
   prototype.css 는 확정된 디자인 시안에서 그대로 가져온 파일입니다.
   수정하지 마세요. 바꿀 일이 있으면 overrides.css 에 적습니다.

 scripts/verify/run.py
   지금 코드가 디자인 시안과 같은 값을 내는지 대조합니다.
   계산 규칙을 고쳤다면 돌려 보세요.

       .venv/bin/python scripts/verify/run.py
"""

out = ROOT / "docs" / "폴더구조.txt"
out.write_text(doc, encoding="utf-8")
print(f"만들었습니다 ({len(doc.splitlines())}줄)")
