"""기술 스택 문서를 실제 설치된 버전에서 생성합니다."""
import json, subprocess, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def pipver(name):
    out = subprocess.run([str(ROOT/".venv/bin/pip"),"show",name],capture_output=True,text=True).stdout
    for line in out.splitlines():
        if line.startswith("Version:"): return line.split(":",1)[1].strip()
    return "-"

pyv = subprocess.run([str(ROOT/".venv/bin/python"),"-V"],capture_output=True,text=True).stdout.strip().replace("Python ","")
nodev = subprocess.run(["node","-v"],capture_output=True,text=True).stdout.strip().lstrip("v")
pkg = json.load(open(ROOT/"frontend/package.json"))

def npmver(name):
    try:
        p = json.load(open(ROOT/f"frontend/node_modules/{name}/package.json"))
        return p.get("version","-")
    except Exception:
        return (pkg.get("dependencies",{}) | pkg.get("devDependencies",{})).get(name,"-").lstrip("^~")

BACK = [
 ("FastAPI","fastapi","웹 프레임워크 — 화면의 요청을 받는 창구"),
 ("Uvicorn","uvicorn","웹 서버 — FastAPI 를 실제로 돌립니다"),
 ("SQLAlchemy","sqlalchemy","데이터베이스 접근 (ORM)"),
 ("Alembic","alembic","데이터베이스 표 변경 이력 관리"),
 ("Pydantic","pydantic","입력값 검증"),
 ("pydantic-settings","pydantic-settings",".env 설정 읽기"),
 ("psycopg","psycopg","PostgreSQL 드라이버"),
 ("APScheduler","apscheduler","공고 자동 수집 예약"),
 ("argon2-cffi","argon2-cffi","비밀번호 해싱"),
 ("itsdangerous","itsdangerous","세션 쿠키 서명(위조 방지)"),
 ("certifi","certifi","SSL 인증서 — 공고 수집에 필요"),
 ("python-dotenv","python-dotenv",".env 파일 읽기"),
]
FRONT = [
 ("React","react","화면 구성"),
 ("React DOM","react-dom","React 를 브라우저에 그림"),
 ("TypeScript","typescript","자바스크립트 + 타입 검사"),
 ("Vite","vite","개발 서버 · 빌드 도구"),
 ("@vitejs/plugin-react","@vitejs/plugin-react","Vite 의 React 지원"),
]

def table(rows, getver):
    w1 = max(len(r[0]) for r in rows)
    out=[]
    for label, key, desc in rows:
        out.append(f"  {label:<{w1}}  {getver(key):<10}  {desc}")
    return "\n".join(out)

doc = f"""사업관리 대시보드 — 기술 스택
================================================================
만든 날짜: {datetime.date.today()}
아래 버전은 실제로 설치되어 동작 중인 것을 읽어 적었습니다.
================================================================


1. 백엔드 (서버)
----------------------------------------------------------------
  언어: Python {pyv}

{table(BACK, pipver)}


2. 프론트엔드 (화면)
----------------------------------------------------------------
  실행 환경: Node.js {nodev}

{table(FRONT, npmver)}

  상태 관리 라이브러리와 UI 라이브러리는 쓰지 않았습니다.
  화면 스타일이 프로토타입에서 그대로 복사한 CSS 라,
  Tailwind 같은 것을 섞으면 글씨 크기·색이 미묘하게 틀어집니다.

  빌드 결과 (사용자가 내려받는 양):
    자바스크립트   210 KB  (압축 후 66 KB)
    스타일(CSS)    239 KB  (압축 후 63 KB)


3. 데이터베이스
----------------------------------------------------------------
  배포용: PostgreSQL 16
  개발용: SQLite

  같은 코드가 둘 다 지원합니다. PostgreSQL 전용 기능을 쓰지 않았고,
  .env 의 DATABASE_URL 만 바꾸면 전환됩니다.

  표 14개 — 사업 / 비목 / 추진과제 / 성과지표 / 진행단계 / 할일 /
            보고회차 / 집행내역 / 지표실적 / 수정이력 /
            공고 / 관심공고 / 화면설정 / 수집기록

  ※ 주의: PostgreSQL 로는 아직 한 번도 실행해 보지 못했습니다.
     개발 PC 에 Docker 가 없어서입니다.
     서버가 정해지면 가장 먼저 이것부터 확인해야 합니다.


4. 공고 수집
----------------------------------------------------------------
  외부 라이브러리 없이 파이썬 표준 기능만 씁니다.
  (원본 스크립트 방식을 그대로 유지했습니다. 설치가 가볍습니다.)

  수집처 4곳:
    한국보건산업진흥원     게시판
    한국보건복지인재원     게시판  ※ 응답을 중간에 끊는 서버 — 대응 로직 있음
    한국보건의료정보원     RSS
    NTIS 국가R&D 통합공고  RSS    ※ 마감일·공고금액을 직접 제공

  기본은 자동 수집이 꺼져 있고, 화면의 [지금 수집] 버튼으로만 받습니다.


5. 로그인
----------------------------------------------------------------
  비밀번호 한 개로 들어가는 방식입니다 (담당자 계정 없음).
  비밀번호는 Argon2 로 해시해서 .env 에 넣고, 원문은 저장하지 않습니다.
  통과하면 서명된 쿠키로 12시간(로그인 유지 시 30일) 유지됩니다.

  나중에 사내 계정(LDAP/SSO)을 붙이게 되면
  backend/app/core/security.py 만 갈아끼우면 됩니다.


================================================================
배포 전에 반드시 바꿔야 할 것 3가지
================================================================
  1) SECRET_KEY
     지금 기본값입니다. 안 바꾸면 세션 쿠키를 위조할 수 있습니다.

  2) APP_PASSWORD_HASH
     지금 비밀번호가 '2026' 입니다. 네 자리 숫자라 짐작하기 쉽습니다.
     scripts/set_password.py 로 바꿉니다.

  3) COOKIE_SECURE=true
     https 로 서비스한다면 켜야 합니다.


================================================================
전산실에 확인할 것
================================================================
  1) 이 서비스를 어디에 올릴 수 있는지 (내부 서버 / 클라우드)

  2) 그 서버에서 외부 인터넷으로 나갈 수 있는지
     ★ 가장 중요합니다. 안 되면 공고 수집이 아예 동작하지 않습니다.

  3) 고정 IP 가 있는지
     기관 API 가 IP 등록을 요구하는 경우가 있습니다.
"""
out = ROOT/"docs"/"기술스택.txt"
out.write_text(doc, encoding="utf-8")
print(f"만들었습니다: {out.relative_to(ROOT)}")
