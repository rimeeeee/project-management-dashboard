"""
사업관리 대시보드 — 백엔드 진입점.

개발 중에는 프론트엔드를 Vite(5173)가 따로 띄우고, 이 서버는 API 만 맡습니다.

배포할 때 무엇을 내보낼지는 .env 의 ROLE 로 정합니다.
  all  — 화면과 API 를 한 포트에서 (기본값)
  web  — 화면(frontend/dist)만
  api  — API 만
프론트와 백엔드를 다른 포트로 나눌 때는 web·api 를 각각 한 프로세스씩 띄웁니다.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# settings 는 아래 설정값 변수(settings = get_settings())와 이름이 겹치므로 별칭을 씁니다
from app.api import announcements, auth, entries, meetings, projects, register, reviews
from app.api import settings as settings_api
from app import __version__
from app.core.config import ROOT, get_settings

log = logging.getLogger("bizdash")
settings = get_settings()

DIST = ROOT / "frontend" / "dist"


def ensure_tables() -> None:
    """
    표가 없으면 만듭니다.

    처음 설치할 때 사람이 따로 명령을 돌리지 않아도 되게 하려는 것입니다.
    (실제로 이게 없어서 새 서버에서 첫 요청이 'no such table' 로 실패했습니다)

    이미 있는 표는 건드리지 않습니다. 나중에 표 구조가 바뀌는 경우에는
    alembic upgrade head 로 반영합니다.
    """
    from sqlalchemy import inspect

    from app.db.session import Base, engine
    import app.models  # noqa: F401  — 표 정의를 등록합니다

    before = set(inspect(engine).get_table_names())
    Base.metadata.create_all(engine)
    made = set(inspect(engine).get_table_names()) - before
    if made:
        log.info("표 %d개를 새로 만들었습니다.", len(made))


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(name)s  %(message)s"
    )
    if settings.using_dev_password:
        log.warning(
            "APP_PASSWORD_HASH 가 비어 있어 개발용 기본 비밀번호로 동작합니다. "
            "운영에 올리기 전에 scripts/set_password.py 로 비밀번호를 설정하세요."
        )
    if settings.secret_key.startswith("dev-only"):
        log.warning("SECRET_KEY 가 기본값입니다. 운영에 올리기 전에 반드시 바꾸세요.")
    log.info("역할(ROLE): %s", settings.role)
    # web 역할은 화면 파일만 내보내므로 데이터베이스를 쓰지 않습니다.
    # 여기서 붙으면 쓰지도 않을 연결을 잡고, DB 가 늦게 뜨면 괜히 못 켜집니다.
    if settings.serves_api:
        log.info("데이터베이스: %s", "SQLite (로컬)" if settings.is_sqlite else "PostgreSQL")
        ensure_tables()
    if settings.serves_web and not DIST.is_dir():
        log.warning(
            "frontend/dist 가 없어 화면을 내보낼 수 없습니다. "
            "개발 PC 에서 release 스크립트로 화면을 만들어 올려 주세요."
        )
    yield


app = FastAPI(title="사업관리 대시보드", version=__version__, lifespan=lifespan)

if settings.cors_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_credentials=True,       # 세션 쿠키를 주고받아야 합니다
        allow_methods=["*"],
        allow_headers=["*"],
    )

if settings.serves_api:
    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(entries.router)
    app.include_router(meetings.router)
    app.include_router(meetings.photo_router)
    app.include_router(reviews.router)
    app.include_router(register.router)
    app.include_router(register.settings_router)
    app.include_router(announcements.router)
    app.include_router(announcements.collector_router)
    app.include_router(announcements.filter_router)
    app.include_router(settings_api.router)


# 두 역할 모두 /api/health 로 살아 있는지 확인할 수 있게 해 둡니다.
# 화면 쪽만 죽는 경우가 있어 각각 따로 볼 수 있어야 합니다.
@app.get("/api/health")
def health() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "version": __version__,
            "role": settings.role,
            "db": ("sqlite" if settings.is_sqlite else "postgresql")
            if settings.serves_api
            else None,
        }
    )


# ---------------------------------------------------------------------
# 빌드된 프론트엔드 서빙 (ROLE 이 all·web 이고 frontend/dist 가 있을 때만)
#
# api 역할일 때 이걸 걸면 안 됩니다. 아래 /{full_path:path} 가 모든 주소를
# 받아 index.html 을 돌려주므로, 없는 API 주소도 200 에 HTML 이 와서
# 화면 쪽에서 "JSON 인 줄 알았는데" 하며 엉뚱한 오류가 납니다.
# ---------------------------------------------------------------------
if settings.serves_web and DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    # dist 폴더의 진짜 위치. 아래에서 '이 안에 있는 파일인지' 판단하는 기준입니다.
    DIST_REAL = DIST.resolve()

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> FileResponse:
        """
        화면 주소는 프론트엔드가 처리하므로, 실제 파일이 아니면 index.html 을 돌려줍니다.

        주소에 ../ 를 넣어 dist 폴더 바깥의 파일을 가져가려는 시도를 막아야 합니다.
        실제로 /..%2F..%2F.env 로 .env 파일(비밀번호 해시·SECRET_KEY 가 든 파일)이
        로그인 없이 읽히는 것을 확인했습니다.

        경로를 실제 위치로 풀어서(resolve) dist 안에 있는지 확인합니다.
        %2F 처럼 인코딩해서 넣어도 여기서 걸립니다.
        """
        # /api/... 는 여기까지 오면 안 됩니다. 오면 두 경우입니다.
        #   · ROLE=web  — 이 프로세스에 API 가 없습니다
        #   · 없는 API 주소를 부른 것
        # 어느 쪽이든 index.html 을 200 으로 주면 화면 쪽에서 JSON 인 줄 알고
        # 읽다가 엉뚱한 오류를 냅니다. 404 로 분명히 알려 줍니다.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="그런 API 주소가 없습니다.")

        candidate = (DIST / full_path).resolve()
        inside = candidate == DIST_REAL or DIST_REAL in candidate.parents
        if full_path and inside and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
