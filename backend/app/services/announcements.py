"""
공고 조회 — 걸러내기 · 정렬 · 쪽 나누기.

프로토타입은 이 일을 브라우저에서 했습니다. 공고가 40건쯤이라 가능했지만,
NTIS 통합공고를 붙이면 전 부처라 수천 건이 됩니다. 그만큼을 브라우저로
내려보낼 수 없어 서버에서 걸러 한 쪽씩 보냅니다.

판단 기준(접수예정/접수중/마감, 금액 구간, 키워드를 제목·사업명에만 맞춤)은
프로토타입과 똑같습니다. 옮기기만 했습니다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import KST
from app.models import Announcement, AnnouncementFavorite

# 공고금액 구간 (원). 금액이 없는 공고(0)는 '전체'에서만 보입니다.
AMOUNT_RANGES: dict[str, tuple[int, float]] = {
    "lt1": (0, 1e8),
    "1to3": (1e8, 3e8),
    "3to5": (3e8, 5e8),
    "gte5": (5e8, float("inf")),
}

# 마감 임박순에서 묶음 순서
STATUS_RANK = {"open": 0, "upcoming": 1, "unknown": 2, "closed": 3}


@dataclass
class Query:
    tab: str = "all"           # all / upcoming / open / closed / fav
    q: str = ""                # 제목 내 검색
    sort: str = "due"          # due / posted / amount / score
    ministries: list[str] = None  # type: ignore[assignment]
    amount: str = "all"
    include: list[str] = None  # type: ignore[assignment]
    page: int = 1
    size: int = 40

    def __post_init__(self) -> None:
        self.ministries = self.ministries or []
        self.include = self.include or []


def status_of(a: Announcement, now: datetime) -> dict[str, Any]:
    """
    공고 접수 상태 — 접수예정 / 접수중 / 마감.
    dday 는 그 상태에서 의미 있는 날짜까지의 일수입니다.
    """
    # 수집된 공고는 목록에 마감일이 없어 due 가 빌 수 있습니다 → '기간 미확인'
    if not a.due:
        return {"key": "unknown", "label": "기간 미확인", "dday": 0,
                "ddayText": "원문 확인", "cls": "closed"}

    from_d = a.open_from or a.posted or a.due
    start = datetime.combine(from_d, time.min, tzinfo=KST)
    hh, mm = (a.due_time or "23:59").split(":")[:2] if a.due_time else ("23", "59")
    try:
        due_t = time(int(hh), int(mm))
    except ValueError:
        due_t = time(23, 59)
    due = datetime.combine(a.due, due_t, tzinfo=KST)

    def ceil_days(t: datetime) -> int:
        """프로토타입 Math.ceil((t - now) / 86400000) 과 같습니다."""
        return math.ceil((t - now).total_seconds() / 86400)

    if now < start:
        d = ceil_days(start)
        return {"key": "upcoming", "label": "접수예정", "dday": d,
                "ddayText": ("오늘 시작" if d == 0 else f"시작 D-{d}"), "cls": "open"}
    if now <= due:
        d = ceil_days(due)
        return {"key": "open", "label": "접수중", "dday": d,
                "ddayText": ("오늘 마감" if d == 0 else f"마감 D-{d}"),
                "cls": ("soon" if d <= 7 else "open")}
    return {"key": "closed", "label": "마감", "dday": ceil_days(due),
            "ddayText": "접수마감", "cls": "closed"}


def matched_keywords(a: Announcement, include: list[str]) -> list[str]:
    """
    포함 키워드는 '공고명·사업명'에만 맞춰 봅니다.
    기관명까지 넣으면 '한국보건산업진흥원'의 '보건' 때문에 그 기관 공고가 전부
    통과해 버려서 걸러내는 의미가 없어집니다.
    """
    hay = f"{a.title} {a.program}".lower()
    return [k for k in include if k.lower() in hay]


def _base_filters(q: Query):
    """관심 조건 — 부처 · 금액 구간 (키워드는 파이썬에서 봅니다)"""
    conds = []
    if q.ministries:
        conds.append(Announcement.ministry.in_(q.ministries))
    rng = AMOUNT_RANGES.get(q.amount)
    if rng:
        lo, hi = rng
        conds.append(Announcement.amount > 0)      # 금액 미입력은 '전체'에서만
        conds.append(Announcement.amount >= int(lo))
        if hi != float("inf"):
            conds.append(Announcement.amount < int(hi))
    return conds


def facets(db: Session, q: Query) -> dict[str, Any]:
    """
    부처 칩과 탭에 붙일 건수.

    쪽을 나눠 보내면 화면에 있는 공고만으로는 부처 목록을 만들 수 없습니다.
    (40건만 받으면 칩이 4개밖에 안 나옵니다.) 그래서 따로 집계해 내려보냅니다.
    """
    # 부처 목록은 '금액 구간'만 반영합니다.
    # 부처를 고른 뒤 다른 부처가 목록에서 사라지면 다시 고를 수가 없습니다.
    mq = Query(amount=q.amount)
    rows = db.execute(
        select(Announcement.ministry, func.count())
        .where(*_base_filters(mq))
        .group_by(Announcement.ministry)
        .order_by(func.count().desc())
    ).all()
    ministries = [{"name": m or "출처 미상", "count": c} for m, c in rows]

    # 탭 건수는 상태 판정이 필요해 파이썬에서 셉니다
    now = datetime.now(KST)
    favs = {f.announcement_id for f in db.query(AnnouncementFavorite).all()}
    counts = {"all": 0, "upcoming": 0, "open": 0, "closed": 0, "unknown": 0, "fav": 0}
    for a in db.query(Announcement).where(*_base_filters(q)).all():
        if q.include and not matched_keywords(a, q.include):
            continue
        counts["all"] += 1
        counts[status_of(a, now)["key"]] += 1
        if a.id in favs:
            counts["fav"] += 1
    return {"ministries": ministries, "tabs": counts}


def to_out(a: Announcement, now: datetime, include: list[str], fav: bool) -> dict[str, Any]:
    return {
        "id": a.id,
        "ministry": a.ministry,
        "agency": a.agency,
        "no": a.no,
        "title": a.title,
        "program": a.program,
        "posted": a.posted.isoformat() if a.posted else "",
        "openFrom": a.open_from.isoformat() if a.open_from else "",
        "due": a.due.isoformat() if a.due else "",
        "dueTime": a.due_time,
        "amount": a.amount,
        "contact": a.contact,
        "url": a.url,
        "source": a.source,
        "status": status_of(a, now),
        "keywords": matched_keywords(a, include),
        "fav": fav,
    }


def search(db: Session, q: Query) -> dict[str, Any]:
    now = datetime.now(KST)
    favs = {f.announcement_id for f in db.query(AnnouncementFavorite).all()}

    stmt = select(Announcement).where(*_base_filters(q))
    if q.q.strip():
        # 제목 내 검색은 기관명까지 포함해 넓게 찾습니다
        like = f"%{q.q.strip().lower()}%"
        stmt = stmt.where(or_(
            func.lower(Announcement.title).like(like),
            func.lower(Announcement.program).like(like),
            func.lower(Announcement.agency).like(like),
            func.lower(Announcement.ministry).like(like),
        ))
    rows = list(db.execute(stmt).scalars())

    if q.include:
        rows = [a for a in rows if matched_keywords(a, q.include)]

    items = [to_out(a, now, q.include, a.id in favs) for a in rows]

    # 탭은 접수 상태와 1:1 로 대응합니다 (관심 탭만 예외)
    if q.tab in ("upcoming", "open", "closed"):
        items = [x for x in items if x["status"]["key"] == q.tab]
    elif q.tab == "fav":
        items = [x for x in items if x["fav"]]

    def sort_key(x: dict[str, Any]):
        if q.sort == "posted":
            return (x["posted"] == "", _desc(x["posted"]))
        if q.sort == "amount":
            return (-x["amount"],)
        if q.sort == "score":
            return (-len(x["keywords"]),)
        # 마감 임박순: 접수중 → 접수예정 → 기간 미확인 → 마감,
        # 각 묶음 안에서는 날짜가 가까운 것부터
        return (STATUS_RANK[x["status"]["key"]], x["status"]["dday"])

    items.sort(key=sort_key)

    total = len(items)
    size = max(1, min(200, q.size))
    pages = max(1, (total + size - 1) // size)
    page = max(1, min(q.page, pages))
    start = (page - 1) * size
    return {
        "items": items[start:start + size],
        "total": total, "page": page, "pages": pages, "size": size,
        "from": (start + 1) if total else 0,
        "to": min(start + size, total),
    }


def _desc(s: str) -> str:
    """문자열 내림차순 정렬용 — 날짜 문자열을 뒤집습니다."""
    return "".join(chr(255 - ord(c)) if ord(c) < 255 else c for c in s)
