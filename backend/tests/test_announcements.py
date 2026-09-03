"""
공고 화면 — 걸러내기 · 정렬 · 쪽 나누기.

판단 기준은 프로토타입과 같습니다. 옮기기만 했으므로 그 기준이 지켜지는지 봅니다.
"""
from __future__ import annotations

import datetime

import pytest

from app.models import Announcement

A = "/api/announcements"


@pytest.fixture()
def seeded(db):
    today = datetime.date.today()
    rows = [
        # (id, 제목, 부처, 게시일, 접수시작, 마감, 금액)
        ("a1", "의료기기 글로벌 진출 지원사업", "보건산업진흥원", -10, -10, +10, 200_000_000),
        ("a2", "바이오헬스 인재양성 공고", "보건산업진흥원", -20, -20, +3, 400_000_000),
        ("a3", "병원 정보시스템 표준화", "보건의료정보원", -5, +5, +30, 0),          # 접수예정
        ("a4", "지난 공고 (마감)", "보건복지인재원", -60, -60, -5, 90_000_000),
        ("a5", "마감일 없는 공고", "보건복지인재원", -3, -3, None, 0),               # 기간 미확인
    ]
    for aid, title, ministry, posted, opened, due, amount in rows:
        db.add(Announcement(
            id=aid, title=title, ministry=ministry, agency=ministry, program="",
            posted=today + datetime.timedelta(days=posted),
            open_from=today + datetime.timedelta(days=opened),
            due=None if due is None else today + datetime.timedelta(days=due),
            due_time="18:00" if due is not None else "",
            amount=amount, url=f"https://example.test/{aid}", source="khidi-board",
        ))
    db.commit()
    return db


# ---------------------------------------------------------------- 상태 판정
def test_접수중_접수예정_마감_기간미확인을_구분한다(client, seeded):
    got = {x["id"]: x["status"]["key"] for x in client.get(f"{A}?size=50").json()["items"]}
    assert got["a1"] == "open"
    assert got["a3"] == "upcoming"
    assert got["a4"] == "closed"
    assert got["a5"] == "unknown"      # 마감일이 없으면 '기간 미확인'


def test_마감이_가까우면_soon_으로_표시한다(client, seeded):
    items = {x["id"]: x for x in client.get(f"{A}?size=50").json()["items"]}
    assert items["a2"]["status"]["cls"] == "soon"      # D-3
    assert items["a1"]["status"]["cls"] == "open"      # D-10


# ---------------------------------------------------------------- 정렬
def test_기본_정렬은_공고일_최신순이다(client, seeded):
    """
    화면을 열었을 때 새로 올라온 공고가 위에 와야 합니다.
    sort 를 주지 않았을 때의 기본값을 확인합니다.
    """
    posted = [x["posted"] for x in client.get(f"{A}?size=50").json()["items"]]
    assert posted == sorted(posted, reverse=True)


def test_마감_임박순은_접수중_접수예정_기간미확인_마감_순이다(client, seeded):
    keys = [x["status"]["key"] for x in client.get(f"{A}?sort=due&size=50").json()["items"]]
    rank = {"open": 0, "upcoming": 1, "unknown": 2, "closed": 3}
    assert keys == sorted(keys, key=lambda k: rank[k])
    # 접수중 묶음 안에서는 마감이 가까운 것부터
    open_ids = [x["id"] for x in client.get(f"{A}?sort=due&size=50").json()["items"]
                if x["status"]["key"] == "open"]
    assert open_ids[0] == "a2"      # D-3 가 D-10 보다 앞


def test_공고금액_큰순으로_정렬한다(client, seeded):
    amounts = [x["amount"] for x in client.get(f"{A}?sort=amount&size=50").json()["items"]]
    assert amounts == sorted(amounts, reverse=True)


# ---------------------------------------------------------------- 걸러내기
def test_키워드는_공고명과_사업명에만_맞춘다(client, seeded):
    """
    기관명까지 넣으면 '한국보건산업진흥원'의 '보건' 때문에 그 기관 공고가 전부
    통과해 버려서 걸러내는 의미가 없어집니다.
    """
    r = client.get(f"{A}?include=의료기기&size=50").json()
    assert [x["id"] for x in r["items"]] == ["a1"]
    assert r["items"][0]["keywords"] == ["의료기기"]

    # '보건'은 기관명에만 있으므로 아무것도 걸리지 않아야 합니다
    assert client.get(f"{A}?include=보건&size=50").json()["total"] == 0


def test_부처로_걸러낸다(client, seeded):
    r = client.get(f"{A}?ministries=보건복지인재원&size=50").json()
    assert {x["id"] for x in r["items"]} == {"a4", "a5"}


def test_금액_구간으로_걸러내고_금액_미입력은_제외한다(client, seeded):
    """금액이 없는 공고(0)는 '전체'에서만 보입니다."""
    r = client.get(f"{A}?amount=1to3&size=50").json()
    assert [x["id"] for x in r["items"]] == ["a1"]      # 2억
    assert all(x["amount"] > 0 for x in client.get(f"{A}?amount=gte5&size=50").json()["items"])


def test_탭은_접수_상태와_대응한다(client, seeded):
    # 이 시험은 '어느 공고가 그 탭에 들어오는가'를 봅니다. 순서는 정렬 시험에서
    # 따로 확인하므로, 기본 정렬이 바뀌어도 흔들리지 않게 순서를 빼고 견줍니다.
    assert sorted(x["id"] for x in client.get(f"{A}?tab=open&size=50").json()["items"]) == ["a1", "a2"]
    assert [x["id"] for x in client.get(f"{A}?tab=upcoming&size=50").json()["items"]] == ["a3"]
    assert [x["id"] for x in client.get(f"{A}?tab=closed&size=50").json()["items"]] == ["a4"]


def test_제목_내_검색은_기관명까지_포함해_넓게_찾는다(client, seeded):
    assert client.get(f"{A}?q=바이오&size=50").json()["total"] == 1
    assert client.get(f"{A}?q=보건의료정보원&size=50").json()["total"] == 1


# ---------------------------------------------------------------- 쪽 나누기
def test_쪽을_나눠_보낸다(client, seeded):
    r1 = client.get(f"{A}?size=2&page=1").json()
    assert len(r1["items"]) == 2
    assert r1["total"] == 5 and r1["pages"] == 3
    assert (r1["from"], r1["to"]) == (1, 2)

    r2 = client.get(f"{A}?size=2&page=2").json()
    assert (r2["from"], r2["to"]) == (3, 4)
    assert {x["id"] for x in r1["items"]} & {x["id"] for x in r2["items"]} == set()

    r3 = client.get(f"{A}?size=2&page=3").json()
    assert len(r3["items"]) == 1 and (r3["from"], r3["to"]) == (5, 5)


def test_없는_쪽을_요청하면_마지막_쪽을_돌려준다(client, seeded):
    r = client.get(f"{A}?size=2&page=99").json()
    assert r["page"] == 3


def test_부처_칩과_탭_건수를_함께_내려준다(client, seeded):
    """
    쪽을 나눠 보내면 화면에 있는 공고만으로는 부처 목록을 만들 수 없습니다.
    (40건만 받으면 칩이 4개밖에 안 나옵니다.)
    """
    f = client.get(f"{A}?size=2").json()["facets"]
    assert {m["name"]: m["count"] for m in f["ministries"]} == {
        "보건산업진흥원": 2, "보건의료정보원": 1, "보건복지인재원": 2}
    assert f["tabs"]["all"] == 5
    assert f["tabs"]["open"] == 2


def test_부처를_골라도_부처_목록은_줄지_않는다(client, seeded):
    """고른 뒤 다른 부처가 사라지면 다시 고를 수가 없습니다."""
    f = client.get(f"{A}?ministries=보건복지인재원&size=50").json()["facets"]
    assert len(f["ministries"]) == 3


# ---------------------------------------------------------------- 관심 · 직접 등록
def test_관심을_켜고_끈다(client, seeded):
    assert client.post(f"{A}/a1/favorite").json()["fav"] is True
    assert [x["id"] for x in client.get(f"{A}?tab=fav&size=50").json()["items"]] == ["a1"]
    assert client.post(f"{A}/a1/favorite").json()["fav"] is False
    assert client.get(f"{A}?tab=fav&size=50").json()["total"] == 0


def test_공고를_직접_등록한다(client, seeded):
    r = client.post(A, json={
        "title": "직접 넣은 공고", "ministry": "보건복지부",
        "openFrom": "2026-09-01", "due": "2026-09-30", "amount": 380_000_000,
    })
    assert r.status_code == 200
    got = next(x for x in client.get(f"{A}?size=50").json()["items"] if x["id"] == r.json()["id"])
    assert got["amount"] == 380_000_000        # 3.8억 → 원
    assert got["source"] == "manual"


def test_마감일이_시작일보다_빠르면_막는다(client, seeded):
    r = client.post(A, json={"title": "x", "openFrom": "2026-09-30", "due": "2026-09-01"})
    assert r.status_code == 400


def test_직접_등록한_공고는_수집이_덮어쓰지_않는다(client, seeded):
    """손으로 채워 넣은 공고금액·문의처가 다음 수집에 날아가면 안 됩니다."""
    from app.collector import runner
    from app.db.session import SessionLocal

    client.put(f"{A}/a1", json={
        "title": "손으로 고친 제목", "ministry": "보건산업진흥원",
        "openFrom": "2026-08-01", "due": "2026-12-31", "amount": 500_000_000,
        "contact": "02-000-0000", "url": "https://example.test/a1",
    })
    s = SessionLocal()
    runner.upsert(s, [{
        "id": "zzz", "title": "수집이 가져온 원래 제목", "url": "https://example.test/a1",
        "posted": "2026-08-01", "source": "khidi-board", "ministry": "보건산업진흥원",
    }], datetime.datetime.now(datetime.timezone.utc))
    s.commit()
    s.close()

    got = next(x for x in client.get(f"{A}?size=50").json()["items"] if x["id"] == "a1")
    assert got["title"] == "손으로 고친 제목"
    assert got["amount"] == 500_000_000
    assert got["contact"] == "02-000-0000"


def test_부처_칩은_가나다순이고_기타가_맨_뒤다(client, db):
    """
    건수 많은 순으로 두면 수집할 때마다 칩 자리가 바뀌어 찾기 어렵습니다.
    """
    import datetime

    today = datetime.date.today()
    for i, m in enumerate(["기타", "해양수산부", "과학기술정보통신부", "경찰청", "산업통상부"]):
        db.add(Announcement(
            id=f"m{i}", title=f"{m} 공고", ministry=m, agency=m,
            posted=today, open_from=today, due=today + datetime.timedelta(days=10),
            amount=0, url=f"https://example.test/m{i}", source="ntis-rss",
        ))
    db.commit()

    names = [m["name"] for m in client.get(f"{A}?size=1").json()["facets"]["ministries"]]
    assert names == ["경찰청", "과학기술정보통신부", "산업통상부", "해양수산부", "기타"]


def test_수집기간_설정이_실제로_반영된다(monkeypatch):
    """
    COLLECT_DAYS 를 .env 로 바꿀 수 있게 했습니다.
    기간 안의 글만 담기는지 확인합니다.
    """
    from app.collector import sources

    monkeypatch.setattr(sources, "COLLECT_DAYS", 365)
    assert sources.in_period((datetime.date.today() - datetime.timedelta(days=300)).isoformat())
    assert not sources.in_period((datetime.date.today() - datetime.timedelta(days=400)).isoformat())

    monkeypatch.setattr(sources, "COLLECT_DAYS", 90)
    assert not sources.in_period((datetime.date.today() - datetime.timedelta(days=300)).isoformat())
    # 게시일을 못 읽은 글은 버리지 않습니다 (놓치는 편보다 낫습니다)
    assert sources.in_period("")
