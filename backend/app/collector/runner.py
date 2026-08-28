"""
수집을 돌리고 결과를 데이터베이스에 넣습니다.

원본 스크립트는 JSON 파일을 만들어 사람이 화면에 붙여넣는 방식이었습니다.
여기서는 그 자리를 데이터베이스 저장으로 바꿉니다. 파싱은 손대지 않았습니다.

수집이 조용히 멈춰 있는데 아무도 모르는 상황이 제일 위험합니다.
그래서 실행할 때마다 collector_runs 에 기록을 남기고 화면 위에 보여 줍니다.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.collector import sources
from app.models import Announcement, CollectorRun

log = logging.getLogger("bizdash.collector")


def _date(v: str | None) -> datetime.date | None:
    if not v:
        return None
    try:
        return datetime.date.fromisoformat(v)
    except ValueError:
        return None


def match_key(a: Announcement | dict) -> str:
    """
    같은 공고인지 판단하는 기준 — 프로토타입 runAnnImport() 와 같습니다.
    주소가 있으면 주소, 없으면 제목+게시일.
    """
    if isinstance(a, dict):
        url = (a.get("url") or "").strip()
        return url or f"{a.get('title') or ''}|{a.get('posted') or ''}"
    url = (a.url or "").strip()
    return url or f"{a.title}|{a.posted.isoformat() if a.posted else ''}"


def upsert(db: Session, items: list[dict], collected_at: datetime.datetime) -> tuple[int, int, int]:
    """
    (새로 넣은 수, 갱신한 수, 그대로 둔 수)

    사람이 직접 등록·수정한 공고(source="manual")는 건드리지 않습니다.
    수집 결과로 덮어쓰면 손으로 채워 넣은 공고금액·문의처가 날아갑니다.
    """
    existing = {match_key(a): a for a in db.query(Announcement).all()}
    added = updated = kept = 0

    for raw in items:
        title = str(raw.get("title") or "").strip()
        if not title:
            continue
        key = match_key(raw)
        prev = existing.get(key)

        if prev is None:
            row = Announcement(
                id=raw["id"],
                ministry=raw.get("ministry") or "",
                agency=raw.get("agency") or "",
                no=raw.get("no") or "",
                title=title,
                program=raw.get("program") or "",
                posted=_date(raw.get("posted")),
                open_from=_date(raw.get("openFrom")) or _date(raw.get("posted")),
                due=_date(raw.get("due")),
                due_time=raw.get("dueTime") or "",
                amount=int(raw.get("amount") or 0),
                contact=raw.get("contact") or "",
                url=raw.get("url") or "",
                source=raw.get("source") or "import",
                collected_at=collected_at,
            )
            # 같은 id 가 이미 있으면(다른 주소로 바뀐 공고 등) 새 id 를 만듭니다
            if db.get(Announcement, row.id) is not None:
                row.id = row.id + "x"
            db.add(row)
            existing[key] = row
            added += 1
            continue

        if prev.source == "manual":
            kept += 1          # 직접 등록·수정한 공고는 그대로 둡니다
            continue

        prev.ministry = raw.get("ministry") or prev.ministry
        prev.agency = raw.get("agency") or prev.agency
        prev.title = title
        prev.posted = _date(raw.get("posted")) or prev.posted
        prev.open_from = _date(raw.get("openFrom")) or prev.open_from
        prev.due = _date(raw.get("due")) or prev.due
        prev.due_time = raw.get("dueTime") or prev.due_time
        prev.url = raw.get("url") or prev.url
        prev.source = raw.get("source") or prev.source
        prev.collected_at = collected_at
        updated += 1

    return added, updated, kept


def run(db: Session, trigger: str = "schedule") -> dict[str, Any]:
    """
    수집 한 번. 소스 하나가 실패해도 나머지는 계속 수집됩니다.
    """
    started = datetime.datetime.now(datetime.timezone.utc)
    record = CollectorRun(started_at=started, trigger=trigger)
    db.add(record)
    db.commit()

    per_source: list[dict[str, Any]] = []
    collected: list[dict] = []

    for key, name, fn in sources.SOURCES:
        try:
            res = fn()
            per_source.append({
                "key": key, "name": name, "count": len(res.items),
                "truncated": res.truncated, "notes": res.notes, "error": "",
            })
            collected.extend(res.items)
            log.info("[완료] %-12s %2d건%s", name, len(res.items),
                     " (응답 잘림 있었음)" if res.truncated else "")
        except Exception as e:  # noqa: BLE001 - 하나가 죽어도 나머지는 계속
            per_source.append({
                "key": key, "name": name, "count": 0, "truncated": False,
                "notes": [], "error": f"{type(e).__name__}: {e}",
            })
            log.error("[실패] %s → %s: %s", name, type(e).__name__, e)

    # 중복 제거: 글 번호 우선, 없으면 제목+게시일 (원본 스크립트와 같습니다)
    unique, seen = [], set()
    for a in collected:
        k1 = (a["source"].split("-")[0], a.pop("_key"))
        k2 = (a["title"], a["posted"])
        if k1 in seen or k2 in seen:
            continue
        seen.add(k1)
        seen.add(k2)
        unique.append(a)
    unique.sort(key=lambda a: a["posted"], reverse=True)

    added, updated, kept = upsert(db, unique, started)

    record.finished_at = datetime.datetime.now(datetime.timezone.utc)
    record.ok = any(s["count"] > 0 for s in per_source)
    record.added, record.updated, record.total_seen = added, updated, len(unique)
    record.detail = {"sources": per_source, "kept": kept}
    db.commit()

    log.info("총 %d건 — 새 공고 %d건 · 갱신 %d건 · 직접 등록 유지 %d건",
             len(unique), added, updated, kept)
    return {
        "runId": record.id, "totalSeen": len(unique),
        "added": added, "updated": updated, "kept": kept, "sources": per_source,
    }
