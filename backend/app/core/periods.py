"""
보고 회차(기간) 계산 — 프로토타입의 periodOf() / periodList() 를 그대로 옮긴 것입니다.

  주간 : 월요일~일요일
  격주 : 사업 시작일부터 2주 단위
  월간 : 매월 1일~말일

여기서 만드는 key 가 곧 데이터베이스의 회차 키(report_entries.period_key)입니다.
프로토타입이 쓰던 키 모양(W2026-08-24 / B12 / M2026-08)을 그대로 유지하므로,
프로토타입 데이터를 옮겨도 회차가 어긋나지 않습니다.

표기 규칙도 프로토타입 그대로입니다.
  label : 짧은 표기 (확인사항·로그)              예) 08.24 ~ 08.30
  full  : 주차를 포함한 표기 (드롭다운·입력 내역) 예) 8월 4주차 · 08.24 ~ 08.30
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

WEEKLY = "주간"
BIWEEKLY = "격주"
MONTHLY = "월간"


@dataclass(frozen=True)
class Period:
    key: str
    start: date
    end: date
    label: str
    full: str


def _md(d: date) -> str:
    """08.24 형태"""
    return f"{d.month:02d}.{d.day:02d}"


def start_of_week(d: date) -> date:
    """그 주의 월요일. (파이썬 weekday(): 월=0)"""
    return d - timedelta(days=d.weekday())


def week_of_month(monday: date) -> int:
    """그 달의 몇 번째 주인지 — 해당 주의 월요일이 그 달의 n번째 월요일"""
    return (monday.day - 1) // 7 + 1


def period_of(cycle: str, project_start: date, d: date) -> Period:
    if cycle == MONTHLY:
        s = d.replace(day=1)
        e = d.replace(day=calendar.monthrange(d.year, d.month)[1])
        label = f"{s.year}년 {s.month}월"
        return Period(f"M{s.year}-{s.month:02d}", s, e, label, label)

    if cycle == BIWEEKLY:
        # 사업 시작일을 기준점으로 2주씩 끊습니다.
        # 시작일보다 앞선 날짜면 idx 가 음수가 되는데, 이것도 프로토타입과 같습니다.
        idx = (d - project_start).days // 14
        s = project_start + timedelta(days=idx * 14)
        e = s + timedelta(days=13)
        label = f"{_md(s)} ~ {_md(e)}"
        return Period(f"B{idx}", s, e, label, f"{idx + 1}회차 · {label}")

    # 주간 (기본값)
    s = start_of_week(d)
    e = s + timedelta(days=6)
    label = f"{_md(s)} ~ {_md(e)}"
    return Period(f"W{s.isoformat()}", s, e, label, f"{s.month}월 {week_of_month(s)}주차 · {label}")


def period_list(cycle: str, project_start: date, today: date, n: int) -> list[Period]:
    """오늘 회차부터 과거로 n개"""
    out: list[Period] = []
    cur = period_of(cycle, project_start, today)
    for _ in range(n):
        out.append(cur)
        prev_day = cur.start - timedelta(days=1)
        cur = period_of(cycle, project_start, prev_day)
    return out


def cycle_word(cycle: str) -> str:
    """프로토타입 cycleWord() — 알 수 없는 값이 들어오면 주간으로 봅니다."""
    return cycle if cycle in (MONTHLY, BIWEEKLY) else WEEKLY
