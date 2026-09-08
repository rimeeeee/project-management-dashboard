"""
예산 — 계정과목은 사업마다 하나, 그 아래 세목, 그 아래 집행 내역.

    사업 (계정과목: 인건비)
      └ 세목 (연구수당 · 4대보험)   ← 편성액과 산출 근거
          └ 집행 내역 (지출일 · 금액)

합계가 어긋나면 정산이 통째로 틀어지므로, 층을 오르내릴 때마다 합이
보존되는지를 봅니다.
"""
from __future__ import annotations

P = "/api/projects"


def cats():
    return [
        {"name": "연구수당", "gov": 80_000_000, "own": 0,
         "basis": "단가 2,000,000 × 5명 × 8개월"},
        {"name": "4대보험", "gov": 40_000_000, "own": 0,
         "basis": "연구수당 × 9.5%"},
        {"name": "국내출장", "gov": 20_000_000, "own": 10_000_000,
         "basis": "1인 200,000 × 20회 × 5명"},
    ]


def payload(**kw):
    body = {
        "name": "예산 시험 사업", "agency": "복지부",
        "folderUrl": "", "account": "인건비",
        "start": "2026-06-01", "end": "2027-05-31",
        "budget": 150_000_000, "cycle": "주간",
        "kpis": [{"name": "논문", "target": 4, "unit": "건"}],
        "tasks": [{"name": "과제 A", "stage": 1}],
        "categories": cats(),
    }
    body.update(kw)
    return body


def 사업(client, **kw):
    r = client.post(P, json=payload(**kw))
    assert r.status_code == 200, r.text
    return r.json()


def 넣기(client, pid, period, spends):
    r = client.put(f"{P}/{pid}/entries/{period}", json={
        "spends": spends, "kpi": {}, "act": "", "issue": "", "plan": "",
        "baseVersion": 0,
    })
    assert r.status_code == 200, r.text
    return r.json()["project"]


# ── 계정과목 ─────────────────────────────────────────────────────
def test_계정과목은_사업마다_하나다(client):
    d = 사업(client)
    assert d["account"] == "인건비"


def test_계정과목을_고칠_수_있다(client):
    d = 사업(client)
    r = client.put(f"{P}/{d['id']}", json=payload(account="사업운영비"))
    assert r.status_code == 200, r.text
    assert r.json()["account"] == "사업운영비"


def test_계정과목은_비워_둘_수_있다(client):
    """아직 정하지 않은 사업이 있습니다. 그것 때문에 등록을 막지는 않습니다."""
    d = 사업(client, account="")
    assert d["account"] == ""


def test_사업_집행액이_곧_계정과목_집행액이다(client):
    """
    계정과목이 하나뿐이라 이 사업에서 쓴 돈은 모두 그 과목으로 잡힙니다.
    따로 합계를 두지 않고 spent 를 그대로 씁니다.
    """
    d = 사업(client)
    d = 넣기(client, d["id"], "W2026-06-01", [
        {"cat": "연구수당", "amt": 10_000_000, "on": "2026-06-03"},
        {"cat": "4대보험", "amt": 1_000_000, "on": "2026-06-03"},
        {"cat": "국내출장", "amt": 400_000, "on": "2026-06-05"},
    ])
    assert d["spent"] == 11_400_000
    assert sum(r["used"] for r in d["catRows"]) == 11_400_000


# ── 세목 ─────────────────────────────────────────────────────────
def test_세목별로_편성액과_집행액이_나온다(client):
    d = 사업(client)
    d = 넣기(client, d["id"], "W2026-06-01", [
        {"cat": "연구수당", "amt": 5_000_000, "on": "2026-06-03"},
    ])
    줄 = {r["name"]: r for r in d["catRows"]}
    assert 줄["연구수당"]["allocated"] == 80_000_000
    assert 줄["연구수당"]["used"] == 5_000_000
    assert 줄["국내출장"]["allocated"] == 30_000_000       # 국고 20 + 자부담 10
    assert 줄["국내출장"]["used"] == 0


def test_산출_근거는_그대로_남는다(client):
    """계산에 쓰지 않고, 다음에 금액을 넣을 때 보고 쓰는 쪽지입니다."""
    d = 사업(client)
    줄 = {r["name"]: r for r in d["catRows"]}
    assert 줄["연구수당"]["basis"] == "단가 2,000,000 × 5명 × 8개월"
    # 사업을 고칠 때 입력칸을 다시 채우려면 categories 에도 있어야 합니다.
    연구수당 = next(c for c in d["categories"] if c["name"] == "연구수당")
    assert 연구수당["basis"] == "단가 2,000,000 × 5명 × 8개월"


def test_지운_세목의_집행액도_남는다(client):
    """감추면 합계가 맞지 않아 '어디서 새는 돈' 처럼 보입니다."""
    d = 사업(client)
    pid = d["id"]
    넣기(client, pid, "W2026-06-01", [{"cat": "국내출장", "amt": 500_000, "on": "2026-06-02"}])

    남길것 = [c for c in cats() if c["name"] != "국내출장"]
    r = client.put(f"{P}/{pid}", json=payload(categories=남길것))
    assert r.status_code == 200, r.text
    d = r.json()

    assert sum(x["used"] for x in d["catRows"]) == 500_000
    assert d["monthly"]["grand"] == 500_000


# ── 월별 ─────────────────────────────────────────────────────────
def test_월별로_지출일에_따라_나뉜다(client):
    d = 사업(client)
    d = 넣기(client, d["id"], "W2026-06-01", [
        {"cat": "연구수당", "amt": 3_000_000, "on": "2026-06-10"},
        {"cat": "연구수당", "amt": 2_000_000, "on": "2026-07-10"},
    ])
    m = d["monthly"]
    줄 = next(r for r in m["rows"] if r["cat"] == "연구수당")
    assert 줄["byMonth"]["2026-06"] == 3_000_000
    assert 줄["byMonth"]["2026-07"] == 2_000_000
    assert m["grand"] == 5_000_000


def test_달을_걸친_회차도_지출일로_갈린다(client):
    """
    이 기능의 핵심입니다. 주간 회차가 8/31~9/6 처럼 달을 걸치면, 회차
    날짜로 묶을 경우 9월에 쓴 돈이 8월로 잡힙니다. 정산에서 묻는 것은
    회차가 아니라 지출일입니다.
    """
    d = 사업(client)
    d = 넣기(client, d["id"], "W2026-08-31", [
        {"cat": "연구수당", "amt": 1_000_000, "on": "2026-08-31"},
        {"cat": "연구수당", "amt": 7_000_000, "on": "2026-09-02"},
    ])
    줄 = next(r for r in d["monthly"]["rows"] if r["cat"] == "연구수당")
    assert 줄["byMonth"]["2026-08"] == 1_000_000
    assert 줄["byMonth"]["2026-09"] == 7_000_000


def test_지출일을_비우면_회차_날짜로_간다(client):
    """매번 적게 하면 번거롭고, 대개는 회차 안에서 쓴 돈입니다."""
    d = 사업(client)
    d = 넣기(client, d["id"], "W2026-06-01", [{"cat": "연구수당", "amt": 900_000, "on": ""}])
    assert d["entries"][0]["spends"][0]["on"] == "2026-06-01"
    줄 = next(r for r in d["monthly"]["rows"] if r["cat"] == "연구수당")
    assert 줄["byMonth"]["2026-06"] == 900_000


def test_지출일이_엉뚱하면_막는다(client):
    """월별 합산이 통째로 어긋납니다."""
    d = 사업(client)
    r = client.put(f"{P}/{d['id']}/entries/W2026-06-01", json={
        "spends": [{"cat": "연구수당", "amt": 1000, "on": "2026-13-40"}],
        "kpi": {}, "act": "", "issue": "", "plan": "", "baseVersion": 0,
    })
    assert r.status_code == 400
    assert "지출일" in r.json()["detail"]


def test_월별_합계는_집행_총액과_같다(client):
    """층을 오르내려도 합이 보존되어야 합니다."""
    d = 사업(client)
    d = 넣기(client, d["id"], "W2026-06-01", [
        {"cat": "연구수당", "amt": 5_000_000, "on": "2026-06-10"},
        {"cat": "4대보험", "amt": 500_000, "on": "2026-07-01"},
        {"cat": "국내출장", "amt": 300_000, "on": "2026-07-20"},
    ])
    총액 = 5_800_000
    m = d["monthly"]
    assert m["grand"] == 총액
    assert sum(m["totals"].values()) == 총액
    assert sum(r["total"] for r in m["rows"]) == 총액
    assert sum(r["used"] for r in d["catRows"]) == 총액
    assert d["spent"] == 총액


def test_한_푼도_안_쓴_세목은_월별_표에_넣지_않는다(client):
    """0 만 늘어선 줄은 표를 길게 만들 뿐입니다."""
    d = 사업(client)
    d = 넣기(client, d["id"], "W2026-06-01", [{"cat": "연구수당", "amt": 1_000_000, "on": "2026-06-10"}])
    assert [r["cat"] for r in d["monthly"]["rows"]] == ["연구수당"]
    # 세목별 화면에는 편성액이 있으니 그대로 남습니다.
    assert "국내출장" in [r["name"] for r in d["catRows"]]


def test_월_목록은_사업_시작_달부터_이어진다(client):
    """중간에 안 쓴 달도 0 으로 남깁니다 — 빈 달도 알아야 할 사실입니다."""
    d = 사업(client)
    d = 넣기(client, d["id"], "W2026-06-01", [{"cat": "연구수당", "amt": 1_000, "on": "2026-08-10"}])
    달 = d["monthly"]["months"]
    assert 달[0] == "2026-06"
    assert "2026-07" in 달                      # 안 쓴 달도 빠지지 않습니다
    assert 달 == sorted(달)
    assert len(달) == len(set(달))
