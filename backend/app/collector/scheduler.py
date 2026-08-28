"""
공고 수집을 정해진 때에 자동으로 돌립니다.

기본값은 주 2회(월·목 06:00, 한국시간)입니다. .env 의 COLLECTOR_CRON 으로 바꿉니다.
서버가 여러 개면 한 대에서만 켜야 같은 수집이 겹쳐 돌지 않습니다.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.collector import runner
from app.core.config import KST, get_settings
from app.db.session import SessionLocal

log = logging.getLogger("bizdash.collector")
_scheduler: BackgroundScheduler | None = None


def _job() -> None:
    db = SessionLocal()
    try:
        runner.run(db, trigger="schedule")
    except Exception:  # noqa: BLE001
        log.exception("정기 수집이 실패했습니다")
    finally:
        db.close()


def start() -> BackgroundScheduler | None:
    global _scheduler
    s = get_settings()
    if not s.collector_enabled:
        log.info("공고 자동 수집이 꺼져 있습니다 (COLLECTOR_ENABLED=false)")
        return None
    try:
        trigger = CronTrigger.from_crontab(s.collector_cron, timezone=KST)
    except ValueError:
        log.error("COLLECTOR_CRON 값이 올바르지 않습니다: %r — 자동 수집을 켜지 않습니다.",
                  s.collector_cron)
        return None

    _scheduler = BackgroundScheduler(timezone=KST)
    _scheduler.add_job(_job, trigger, id="collect", max_instances=1, coalesce=True)
    _scheduler.start()
    log.info("공고 자동 수집 예약: %s (한국시간)", s.collector_cron)
    return _scheduler


def stop() -> None:
    if _scheduler:
        _scheduler.shutdown(wait=False)
