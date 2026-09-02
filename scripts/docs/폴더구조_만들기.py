"""
docs/폴더구조.txt 를 실제 폴더를 읽어 만듭니다.

    .venv/bin/python scripts/docs/폴더구조_만들기.py

파일을 추가하거나 옮긴 뒤에 돌려 주세요.
폴더 설명을 붙이려면 아래 NOTE 에 한 줄 추가하면 됩니다.
"""
import sys
import unicodedata
from pathlib import Path

for _s in (sys.stdout, sys.stderr):        # Windows 콘솔(cp949)에서 한글이 깨지지 않게
    _s.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
SKIP = {"node_modules", ".git", ".venv", "__pycache__", ".pytest_cache", "fonts"}
SKIP_FILE = {"package-lock.json", ".DS_Store", "tsconfig.tsbuildinfo",
             "Dockerfile", "docker-compose.yml", ".env"}

# 파일까지 펼치지 않고 폴더 한 줄로만 보여 줄 곳
FOLD = {"backend/tests", "backend/alembic", "backend/app/api", "backend/app/db",
        "backend/app/models", "backend/app/services", "backend/app/core",
        "backend/app/collector", "frontend/src/pages", "frontend/src/components",
        "frontend/src/lib", "frontend/src/styles", "frontend/public",
        "frontend/dist",
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
 "frontend": "화면 (React)",
 "frontend/src/pages": "화면 단위",
 "frontend/src/components": "화면 구성 요소",
 "frontend/src/lib": "서버 통신·표시 변환",
 "frontend/src/styles": "디자인 ★",
 "frontend/public": "로고·글꼴",
 "frontend/dist": "만들어진 화면 — 서버가 이것을 내보냅니다",
 "frontend/package.json": "설치할 프론트엔드 라이브러리",
 "scripts": "도구",
 "scripts/set_password.py": "비밀번호 변경",
 "scripts/ntis_backfill.py": "NTIS 지난 공고 채우기",
 "scripts/make_package.sh": "서버에 올릴 파일만 모아 압축",
 "scripts/fetch_fonts.py": "글꼴 내려받기",
 "scripts/dev.sh": "개발 서버 실행 (macOS·Linux)",
 "scripts/dev.ps1": "개발 서버 실행 (Windows)",
 "scripts/release.ps1": "서버에 올릴 준비 (Windows)",
 "scripts/release.sh": "서버에 올릴 준비 (mac·Linux)",
 "scripts/seed": "개발용 예시 자료",
 "scripts/verify": "디자인 시안 대조 검증 ★",
 "scripts/probe": "NTIS 응답 형식 조사",
 "scripts/docs": "이 문서를 만드는 스크립트",
 "docs": "문서",
 "docs/개발.md": "고칠 때 보는 안내",
 "docs/prototype": "확정된 디자인 시안 (요구사항 원본)",
 "docs/ntis": "NTIS 응답 원문",
 "data": "자료 저장 (bizdash.db)",
 ".env.example": "설정 견본 — .env 로 복사해서 씁니다",
 "README.md": "이 프로그램 소개",
 "requirements.txt": "설치할 파이썬 라이브러리",
}

def _w(s: str) -> int:
    """화면에서 차지하는 칸 수. 한글·한자 등은 두 칸입니다."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


lines = []


def walk(d: Path, prefix: str = "") -> None:
    items = sorted(
        [p for p in d.iterdir()
         if p.name not in SKIP and p.name not in SKIP_FILE and not p.name.startswith(".git")],
        key=lambda p: (p.is_file(), p.name.lower()),
    )
    for i, p in enumerate(items):
        last = i == len(items) - 1
        rel = p.relative_to(ROOT).as_posix()  # Windows 에서도 "/" 로 맞춥니다 (FOLD·NOTE 조회 키)
        name = p.name + ("/" if p.is_dir() else "")
        row = f"{prefix}{'└── ' if last else '├── '}{name}"
        note = NOTE.get(rel, "")
        # 한글은 한 글자가 두 칸을 차지합니다. 글자 수로 맞추면 한글이 섞인
        # 줄만 설명이 밀리므로, 화면에 보이는 폭으로 맞춥니다.
        lines.append((row + " " * max(1, 36 - _w(row)) + note).rstrip())
        if p.is_dir() and rel not in FOLD:
            walk(p, prefix + ("    " if last else "│   "))


walk(ROOT)


HEADER = """================================================================
 사업관리 대시보드 — 폴더 구조
================================================================

"""

out = ROOT / "docs" / "폴더구조.txt"
doc = HEADER + "\n".join(lines) + "\n"
out.write_text(doc, encoding="utf-8")
print(f"만들었습니다 ({len(doc.splitlines())}줄)")
