"""
설정 — 환경변수(.env)에서 읽습니다.

배포 환경이 아직 정해지지 않았으므로, 나중에 서버가 정해졌을 때
코드를 고치지 않고 .env 값만 바꿔서 그대로 올릴 수 있도록 모아 두었습니다.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 의 한 단계 위 = 저장소 최상위
ROOT = Path(__file__).resolve().parents[3]

# 사업 기간·공고 마감 판정이 모두 '오늘'에 걸려 있습니다.
# 서버가 UTC 로 돌면 밤 9시부터 다음 날로 판정되므로 한국 시간으로 고정합니다.
KST = ZoneInfo("Asia/Seoul")

# .env 에 APP_PASSWORD_HASH 를 넣지 않았을 때 쓰는 개발용 비밀번호.
# 서버 시작 시 경고를 띄웁니다.
DEV_PASSWORD = "bizdash2026"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "sqlite+pysqlite:///./data/bizdash.db"

    app_password_hash: str = ""
    secret_key: str = "dev-only-insecure-key-change-me"
    session_hours: int = 12
    remember_days: int = 30
    cookie_secure: bool = False

    cors_origins: str = "http://localhost:5173"

    collector_enabled: bool = True
    collector_cron: str = "0 6 * * 1,4"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def using_dev_password(self) -> bool:
        return not self.app_password_hash.strip()


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # SQLite 파일은 경로를 절대경로로 바꿔 둡니다.
    # 그냥 두면 서버를 어느 폴더에서 켰느냐에 따라 다른 파일을 보게 되어,
    # "어제 넣은 데이터가 사라졌다" 처럼 보이는 일이 생깁니다.
    if s.is_sqlite:
        prefix, _, raw = s.database_url.partition("///")
        path = Path(raw) if os.path.isabs(raw) else (ROOT / raw).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        s.database_url = f"{prefix}///{path}"
    return s
