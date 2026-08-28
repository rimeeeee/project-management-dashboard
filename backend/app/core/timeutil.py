"""
저장된 시각을 한국시간으로 바꿔 보여 줍니다.

시각은 UTC 로 저장합니다. 그런데 SQLite 는 시간대 정보를 저장하지 못해서,
읽어 오면 tzinfo 가 없는(naive) 값이 됩니다. 그 값에 그냥 astimezone() 을 쓰면
파이썬이 '서버가 있는 곳의 시간'으로 오해해서 9시간이 어긋납니다.

PostgreSQL 은 시간대를 그대로 보관하므로 이 문제가 나지 않습니다.
즉 로컬(SQLite)에서만 나는 종류라, 한 곳에서 처리해 두지 않으면
"내 PC 에서는 맞는데 서버에서는 다르다"가 반대로 일어납니다.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import KST


def to_kst(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        # 저장은 항상 UTC 로 했으므로 UTC 로 봅니다
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)


def kst_iso(dt: datetime | None) -> str:
    d = to_kst(dt)
    return d.isoformat() if d else ""


def kst_short(dt: datetime | None) -> str:
    """08/28 14:24 — 화면 안내 문구에 씁니다"""
    d = to_kst(dt)
    return d.strftime("%m/%d %H:%M") if d else ""
