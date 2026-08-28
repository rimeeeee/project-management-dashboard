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
from app.api import auth, entries, projects, register
from app.api import settings as settings_api
from app.core.config import ROOT, get_settings

log = logging.getLogger("bizdash")
settings = get_settings()

DIST = ROOT / "frontend" / "dist"


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
    yield


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

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> FileResponse:
        # 화면 주소는 프론트엔드가 처리하므로 무엇이 오든 index.html 을 돌려줍니다.
        candidate = DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
