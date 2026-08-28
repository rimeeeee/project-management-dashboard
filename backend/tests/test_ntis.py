"""
NTIS 통합공고 읽기.

XSL 샘플(unRndRss.xsl)에는 author/title/link/pubDate 만 있어서 마감일·공고금액이
없을 줄 알았는데, 실제 응답에는 appdue·budget 이 있었습니다.
그래서 제목에서 뽑아내지 않고 그 값을 그대로 씁니다.

여기서는 실제 응답을 잘라 만든 표본(tests/fixtures/ntis_sample.xml)으로 확인합니다.
테스트가 바깥 인터넷에 나가지 않게 하려는 것입니다.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.collector import sources

SAMPLE = Path(__file__).parent / "fixtures" / "ntis_sample.xml"


@pytest.fixture()
def items(monkeypatch):
    monkeypatch.setattr(sources, "get", lambda *a, **k: SAMPLE.read_text(encoding="utf-8"))
    # 표본은 지난 공고라 수집기간 제한을 넉넉히 둡니다
    monkeypatch.setattr(sources, "COLLECT_DAYS", 100000)
    return sources._ntis_items("http://example.test")


def test_필드를_제대로_읽는다(items):
    a = items[0]
    assert a["title"] == "2026년 사회문제해결형 R&BD 지원사업 시행 공고"
    assert a["url"].endswith("roRndUid=1276553")
    assert a["ministry"] == "과학기술정보통신부"       # author = 공고기관(부처)
    assert a["agency"] == "연구개발특구진흥재단"        # category = 전문기관
    assert a["posted"] == "2026-08-21"                # pubDate 는 2026.08.21 형태
    assert a["source"] == "ntis-rss"


def test_마감일을_제목에서_뽑지_않고_appdue_를_쓴다(items):
    """
    기관 게시판은 제목에 적힌 '~9/11' 같은 표기에서 뽑아야 하지만,
    NTIS 는 마감일을 직접 주므로 훨씬 정확합니다.
    """
    a = items[0]
    assert a["openFrom"] == "2026-08-21"      # appbegin
    assert a["due"] == "2026-09-21"           # appdue
    # 제목에 날짜 표기가 없는데도 마감일이 채워져야 합니다
    assert "9/21" not in a["title"] and "9월 21" not in a["title"]


def test_공고금액은_원_단위_그대로_쓴다(items):
    assert items[0]["amount"] == 510_000_000       # budget 그대로 (5.1억)


def test_금액이_없는_공고는_0으로_둔다(items):
    """기술수요조사처럼 금액이 없는 공고가 있습니다. 임의로 채우지 않습니다."""
    no_amount = [a for a in items if a["amount"] == 0]
    assert no_amount, "표본에 금액 없는 공고가 있어야 합니다"
    assert all(a["due"] for a in no_amount)        # 금액이 없어도 마감일은 있습니다


def test_모든_공고에_마감일이_있다(items):
    assert all(a["due"] for a in items)


def test_주소가_고유하다(items):
    urls = [a["url"] for a in items]
    assert len(set(urls)) == len(urls)


def test_수집기간_밖의_공고는_제외한다(monkeypatch):
    monkeypatch.setattr(sources, "get", lambda *a, **k: SAMPLE.read_text(encoding="utf-8"))
    monkeypatch.setattr(sources, "COLLECT_DAYS", 1)     # 하루치만
    r = sources.ntis()
    assert r.items == []
    assert r.notes and "수집기간" in r.notes[0]


def test_최신_100건이_수집기간을_못_덮으면_날짜별로_더_받는다(monkeypatch):
    """
    NTIS 는 한 번에 최대 100건만 줍니다(prt 상한). Fi 는 그 묶음 안에서만
    움직여 100건 너머로 갈 수 없습니다.

    실제로 최신 100건은 72일치였고 수집기간 90일에서 18일이 빠져
    38건을 놓치고 있었습니다. 그래서 덮지 못한 날짜만 dt= 로 채웁니다.
    """
    import datetime

    calls: list[str] = []

    def fake_get(url, *a, **k):
        calls.append(url)
        return SAMPLE.read_text(encoding="utf-8")

    monkeypatch.setattr(sources, "get", fake_get)
    monkeypatch.setattr(sources, "COLLECT_DAYS", 100000)
    monkeypatch.setattr(sources, "NTIS_MAX", 4)      # 표본이 4건이라 '꽉 찼다'고 보게 합니다
    monkeypatch.setattr(sources.time, "sleep", lambda *_: None)
    monkeypatch.setattr(sources, "today", lambda: datetime.date(2026, 8, 22))

    r = sources.ntis()

    # 최신 묶음 1회 + 못 덮은 날짜만큼 dt= 조회가 있어야 합니다
    assert any("dt=" in c for c in calls), "날짜별 조회를 하지 않았습니다"
    assert r.notes and "날짜별로 더 받았습니다" in r.notes[0]
    # 같은 공고가 양쪽에 나와도 한 번만 담겨야 합니다
    urls = [a["url"] for a in r.items]
    assert len(urls) == len(set(urls))


def test_최신_100건이_수집기간을_다_덮으면_날짜별_조회를_하지_않는다(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(sources, "get", lambda url, *a, **k: (calls.append(url),
                                                              SAMPLE.read_text(encoding="utf-8"))[1])
    monkeypatch.setattr(sources, "COLLECT_DAYS", 100000)
    monkeypatch.setattr(sources, "NTIS_MAX", 100)    # 표본 4건 < 100 → 덜 찼음
    sources.ntis()
    assert not any("dt=" in c for c in calls)
