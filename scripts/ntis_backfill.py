"""
NTIS 통합공고의 지난 공고를 채웁니다.

    .venv/bin/python scripts/ntis_backfill.py            # 최근 90일
    .venv/bin/python scripts/ntis_backfill.py --days 180

정기 수집은 최신 100건만 봅니다. NTIS 는 prt 가 최대 100 이고, Fi 는 '전체에서
몇 번째부터'가 아니라 'prt 로 가져온 묶음 안의 시작 행'이라 100건 너머로는
넘어갈 수 없기 때문입니다.

지난 공고는 dt=YYYYMMDD 로 하루씩 받아야 합니다. 처음 도입할 때 한 번,
또는 수집이 오래 멈춰 있었을 때 돌리면 됩니다.

하루에 새로 올라오는 공고가 두어 건이라 정기 수집(주 2회, 최신 100건)만으로
평소에는 빠지지 않습니다.
"""
from __future__ import annotations

import argparse
import datetime
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.collector import runner, sources        # noqa: E402
from app.core.calc import today                  # noqa: E402
from app.db.session import SessionLocal          # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90, help="며칠 전까지 채울지 (기본 90)")
    ap.add_argument("--pause", type=float, default=0.4, help="요청 사이 쉬는 시간(초)")
    args = ap.parse_args()

    end = today()
    days = [end - datetime.timedelta(days=i) for i in range(args.days)]
    print(f"NTIS 지난 공고를 채웁니다: {days[-1]} ~ {end} ({len(days)}일)")

    collected: list[dict] = []
    failed = 0
    for i, day in enumerate(days, 1):
        try:
            items = sources.ntis_by_date(day)
            collected.extend(items)
            if items:
                print(f"  {day} — {len(items)}건")
        except Exception as e:  # noqa: BLE001 - 하루가 실패해도 나머지는 계속
            failed += 1
            print(f"  {day} — 실패 ({type(e).__name__})")
        if i % 20 == 0:
            print(f"  … {i}/{len(days)}일  (지금까지 {len(collected)}건)")
        time.sleep(args.pause)

    # 같은 공고가 여러 날짜에 걸쳐 나올 수 있어 주소 기준으로 한 번 더 거릅니다
    unique, seen = [], set()
    for a in collected:
        k = a.pop("_key")
        if k in seen:
            continue
        seen.add(k)
        unique.append(a)

    db = SessionLocal()
    try:
        added, updated, kept = runner.upsert(db, unique, datetime.datetime.now(datetime.timezone.utc))
        db.commit()
    finally:
        db.close()

    print("-" * 56)
    print(f" 받은 공고 {len(unique)}건 → 새로 넣음 {added}건 · 갱신 {updated}건 · 직접 등록 유지 {kept}건")
    if failed:
        print(f" 실패한 날짜 {failed}일 — 다시 돌리면 그 날짜만 다시 시도합니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
