"""
사업관리 대시보드 — 백엔드 진입점.

개발 중에는 프론트엔드를 Vite(5173)가 따로 띄우고, 이 서버는 API 만 맡습니다.
배포할 때는 frontend/dist 를 그대로 서빙해 한 서버로 끝냅니다.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# settings 는 아래 설정값 변수(settings = get_settings())와 이름이 겹치므로 별칭을 씁니다
from app.api import announcements, auth, entries, projects, register
from app.api import settings as settings_api
from app.collector import scheduler
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
    log.info("데이터베이스: %s", "SQLite (로컬)" if settings.is_sqlite else "PostgreSQL")
    ensure_tables()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.stop()


app = FastAPI(title="사업관리 대시보드", version="0.1.0", lifespan=lifespan)

if settings.cors_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_credentials=True,       # 세션 쿠키를 주고받아야 합니다
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(entries.router)
app.include_router(register.router)
app.include_router(register.settings_router)
app.include_router(announcements.router)
app.include_router(announcements.collector_router)
app.include_router(announcements.filter_router)
app.include_router(settings_api.router)


@app.get("/api/health")
def health() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "db": "sqlite" if settings.is_sqlite else "postgresql",
        }
    )


# ---------------------------------------------------------------------
# 빌드된 프론트엔드 서빙 (frontend/dist 가 있을 때만)
# ---------------------------------------------------------------------
if DIST.is_dir():
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
        candidate = (DIST / full_path).resolve()
        inside = candidate == DIST_REAL or DIST_REAL in candidate.parents
        if full_path and inside and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
