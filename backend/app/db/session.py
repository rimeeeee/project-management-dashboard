"""
데이터베이스 연결.

DATABASE_URL 하나로 로컬(SQLite)과 운영(PostgreSQL)을 오갑니다.
PostgreSQL 전용 자료형(JSONB 등)은 쓰지 않고 SQLAlchemy 공통 자료형만 써서,
로컬에서 만든 것이 운영 서버에서도 그대로 돌아가게 합니다.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
    future=True,
)

# SQLite 는 외래키 제약을 기본으로 끄고 시작합니다.
# 켜 두지 않으면 PostgreSQL 에서만 걸리는 오류가 로컬에서 안 잡힙니다.
if settings.is_sqlite:

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
