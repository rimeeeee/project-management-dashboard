"""
계산 규칙 — 프로토타입의 calc* 함수를 그대로 옮긴 것입니다.

실무 검토를 거쳐 확정된 규칙이라 임의로 바꾸면 안 됩니다. 특히:

  - 진행률(actual)   = 완료 과제 ÷ 전체 과제
  - 계획 진척률(planned) = 사업 기간 중 오늘까지 지난 비율
  - 상태 배지        = 계획 대비 −15%p 미만이면 '조치 필요',
                       −5%p 미만이거나 미해결 확인사항이 있으면 '점검 필요',
                       그 밖에는 '정상'
  - 진행률 숫자와 게이지 색은 '계획 대비'만 봅니다.
    확인사항은 반영하지 않습니다 — 상태 배지와 기준이 다릅니다.
    (진척을 나타내는 숫자에 확인사항을 섞으면 무엇을 뜻하는 숫자인지 흐려집니다.)

날짜 판정은 한국 시간(Asia/Seoul) 기준입니다.
서버가 UTC 로 돌면 밤 9시부터 다음 날로 판정되기 때문입니다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime

from app.core.config import KST

STAGES = ["기획", "착수", "진행", "마무리", "완료"]

# 상태 — 프로토타입의 표기를 그대로 씁니다.
# '주의'·'위험' 같은 표현은 쓰지 않기로 했습니다.
STATUS_OK = ("g", "정상")
STATUS_CHECK = ("w", "점검 필요")
STATUS_ACTION = ("c", "조치 필요")


def js_round(x: float) -> int:
    """
    자바스크립트 Math.round 와 같게 반올림합니다.
    파이썬 기본 round() 는 0.5 를 짝수 쪽으로 보내서(은행가 반올림)
    round(0.5)=0, round(2.5)=2 가 됩니다. 프로토타입과 값이 달라집니다.
    """
    return math.floor(x + 0.5)


def clamp(v: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, v))


def today() -> date:
    return datetime.now(KST).date()


def now() -> datetime:
    return datetime.now(KST)


def calc_actual(total_tasks: int, done_tasks: int) -> int:
    """진행률 = 완료 과제 ÷ 전체 과제"""
    if not total_tasks:
        return 0
    return js_round(100 * done_tasks / total_tasks)


def calc_planned(start: date, end: date, at: datetime | None = None) -> int:
    """계획 진척률 = 사업 기간 중 지금까지 지난 비율"""
    if not (start < end):
        return 0
    at = at or now()
    s = datetime.combine(start, datetime.min.time(), tzinfo=KST)
    e = datetime.combine(end, datetime.min.time(), tzinfo=KST)
    return js_round(clamp((at - s) / (e - s), 0, 1) * 100)


@dataclass(frozen=True)
class Status:
    key: str      # g / w / c
    label: str    # 정상 / 점검 필요 / 조치 필요


def calc_status(actual: int, planned: int, has_open_issue: bool) -> Status:
    diff = actual - planned
    if diff < -15:
        return Status(*STATUS_ACTION)
    if diff < -5 or has_open_issue:
        return Status(*STATUS_CHECK)
    return Status(*STATUS_OK)


def progress_color(actual: int, planned: int) -> str:
    """
    진행률 숫자와 게이지에 쓰는 색.
    상태 배지와 달리 확인사항은 보지 않습니다 — 이 숫자는 진척만 나타내야 합니다.
    "" 는 초록(기본), w 는 노랑, c 는 빨강입니다.
    """
    diff = actual - planned
    if diff < -15:
        return "c"
    if diff < -5:
        return "w"
    return ""


def auto_stage(actual: int, start: date, at: date | None = None) -> int:
    """예전 데이터에 진행 단계가 없을 때만 쓰는 추정값"""
    at = at or today()
    if actual >= 100:
        return 4
    if actual >= 75:
        return 3
    if actual >= 25:
        return 2
    if at >= start or actual > 0:
        return 1
    return 0
