"""사업 현황 집계에서 공통으로 사용하는 날짜 경계를 확인합니다."""
from datetime import date, datetime

from app.core.config import KST
from app.services.projects import dday


def test_종료일_당일까지는_진행중이다():
    result = dday(date(2026, 9, 10), datetime(2026, 9, 10, 23, 59, 59, tzinfo=KST))

    assert result == {"txt": "D-day", "cls": "soon"}


def test_종료일_다음날부터는_즉시_종료다():
    result = dday(date(2026, 9, 10), datetime(2026, 9, 11, 0, 0, 0, tzinfo=KST))

    assert result == {"txt": "종료", "cls": "closed"}
