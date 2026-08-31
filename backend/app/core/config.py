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


    # 기관 게시판(인재원·진흥원·의료정보원)을 며칠 전 게시물까지 가져올지.
    # 공고는 연 단위 사업 주기라 '작년 이맘때 공고'를 찾는 일이 있어 1년으로 둡니다.
    collect_days: int = 365
    # 게시판을 최대 몇 쪽까지 읽을지.
    #
    # 실측(2026-08): 진흥원 게시판은 pageNum 이 10 에서 순환합니다.
    # 11쪽은 1쪽, 16쪽은 6쪽과 같은 내용을 돌려줍니다. rowCnt(쪽당 건수),
    # schStartDate/schEndDate(기간 검색), minIndex/maxIndex 모두 GET·POST 어느
    # 쪽으로도 먹지 않았습니다. 즉 그 게시판이 밖으로 내주는 것은 약 102건
    # (2026-08 기준 약 6.5개월)이 전부입니다.
    #
    # 인재원은 쪽당 50건이라 1년이 2쪽이면 끝나고, 수집기간을 벗어난 글만 나오는
    # 쪽에 닿으면 알아서 멈춥니다. 그래서 12로 두어도 세 기관 모두 한계까지 받습니다.
    board_pages: int = 12
    # NTIS 는 최신 100건 너머를 날짜별(dt=)로 받아야 해서, 기간을 길게 잡으면
    # 정기 수집마다 수백 번 요청하게 됩니다. 정기 수집은 90일로 두고,
    # 더 과거는 scripts/ntis_backfill.py 로 한 번만 채웁니다.
    ntis_days: int = 90

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
