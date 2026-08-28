"""
사업 등록 · 수정 · 삭제.

확인 순서와 문구는 프로토타입 submitRegister() 를 그대로 옮긴 것입니다.
실무에서 익숙해진 순서라 바꾸지 않습니다.
"""
from __future__ import annotations

P = "/api/projects"


def payload(**kw):
    base = {
        "name": "새 사업", "agency": "보건복지부", "folderUrl": "",
        "start": "2026-06-01", "end": "2027-05-31", "budgetEok": 9.5, "cycle": "주간",
        "kpis": [{"name": "논문", "target": 3, "unit": "건"}],
        "tasks": [{"name": "착수보고"}],
        "categories": [{"name": "인건비", "allocated": 400000000}],
    }
    base.update(kw)
    return base


# ---------------------------------------------------------------- 등록
def test_사업을_등록한다(client):
    r = client.post(P, json=payload())
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["name"] == "새 사업"
    assert d["budget"] == 950_000_000          # 9.5억 → 원
    assert d["cycle"] == "주간"
    assert d["entries"] == []
    # 등록 화면에서 받지 않는 값이 채워져야 화면이 그려집니다
    assert d["stage"] == 0
    assert len(d["stageNotes"]) == 5


def test_억을_원으로_바꿔_저장한다(client):
    assert client.post(P, json=payload(budgetEok=0.75)).json()["budget"] == 75_000_000
    assert client.post(P, json=payload(budgetEok=12)).json()["budget"] == 1_200_000_000


# ---------------------------------------------------------------- 확인 규칙
def test_사업명이_없으면_막는다(client):
    r = client.post(P, json=payload(name="  "))
    assert r.status_code == 400
    assert r.json()["detail"] == "사업명을 입력하세요."


def test_종료일이_시작일보다_빠르면_막는다(client):
    r = client.post(P, json=payload(start="2027-01-01", end="2026-01-01"))
    assert r.status_code == 400
    assert "사업 기간을 확인하세요" in r.json()["detail"]


def test_총사업비가_0이면_막는다(client):
    r = client.post(P, json=payload(budgetEok=0))
    assert r.status_code == 400
    assert "총 사업비는 0보다 큰" in r.json()["detail"]


def test_비목_추진과제_성과지표는_각각_하나_이상(client):
    assert client.post(P, json=payload(categories=[])).json()["detail"] == "예산 비목을 1개 이상 입력하세요."
    assert client.post(P, json=payload(tasks=[])).json()["detail"] == "추진과제를 1개 이상 입력하세요."
    assert client.post(P, json=payload(kpis=[])).json()["detail"] == "성과지표를 1개 이상 입력하세요."


def test_목표가_0인_지표는_버린다(client):
    r = client.post(P, json=payload(kpis=[{"name": "빈 지표", "target": 0}, {"name": "논문", "target": 2}]))
    assert [k["name"] for k in r.json()["kpis"]] == ["논문"]


def test_같은_이름의_비목은_한_번만_넣는다(client):
    r = client.post(P, json=payload(categories=[
        {"name": "인건비", "allocated": 100}, {"name": "인건비", "allocated": 200}]))
    assert [c["name"] for c in r.json()["categories"]] == ["인건비"]


def test_배정액을_비우면_0으로_둔다(client):
    """임의로 나눠 채우지 않습니다 — 실제와 다른 잔액이 보이기 때문입니다."""
    r = client.post(P, json=payload(categories=[{"name": "인건비", "allocated": 0}]))
    assert r.json()["categories"][0]["allocated"] == 0


# ---------------------------------------------------------------- 수정
def test_사업을_수정한다(client):
    pid = client.post(P, json=payload()).json()["id"]
    r = client.put(f"{P}/{pid}", json=payload(name="이름 바꾼 사업", budgetEok=20))
    assert r.status_code == 200
    assert r.json()["name"] == "이름 바꾼 사업"
    assert r.json()["budget"] == 2_000_000_000


def test_같은_이름의_과제는_완료_체크를_유지한다(client):
    pid = client.post(P, json=payload(tasks=[{"name": "과제 A"}, {"name": "과제 B"}])).json()["id"]
    client.patch(f"{P}/{pid}/task", json={"index": 0, "done": True})

    # 과제 목록을 고쳐도 '과제 A' 의 완료 표시는 남아야 합니다
    r = client.put(f"{P}/{pid}", json=payload(
        tasks=[{"name": "과제 A"}, {"name": "과제 B"}, {"name": "과제 C"}]))
    tasks = {t["name"]: t["done"] for t in r.json()["tasks"]}
    assert tasks == {"과제 A": True, "과제 B": False, "과제 C": False}


def test_입력_내역이_있으면_보고_주기를_바꿀_수_없다(client):
    """
    회차 키(W…/B…/M…)가 이미 저장되어 있어서, 주기가 바뀌면 기존 회차가
    다른 기간을 가리키게 됩니다. 화면에서도 막지만 서버에서 다시 확인합니다.
    """
    pid = client.post(P, json=payload()).json()["id"]
    client.put(f"{P}/{pid}/entries/W2026-08-24", json={"act": "1회차", "baseVersion": 0})

    r = client.put(f"{P}/{pid}", json=payload(cycle="월간"))
    assert r.status_code == 400
    assert "보고 주기는 변경할 수 없습니다" in r.json()["detail"]


def test_격주_사업은_입력_내역이_있으면_시작일을_바꿀_수_없다(client):
    pid = client.post(P, json=payload(cycle="격주")).json()["id"]
    client.put(f"{P}/{pid}/entries/B0", json={"act": "1회차", "baseVersion": 0})

    r = client.put(f"{P}/{pid}", json=payload(cycle="격주", start="2026-05-15"))
    assert r.status_code == 400
    assert "격주 회차 기준일" in r.json()["detail"]


def test_주간_사업은_입력_내역이_있어도_시작일을_바꿀_수_있다(client):
    """주간·월간 회차 키는 시작일과 상관없으므로 막을 이유가 없습니다."""
    pid = client.post(P, json=payload()).json()["id"]
    client.put(f"{P}/{pid}/entries/W2026-08-24", json={"act": "1회차", "baseVersion": 0})

    r = client.put(f"{P}/{pid}", json=payload(start="2026-05-01"))
    assert r.status_code == 200
    assert r.json()["start"] == "2026-05-01"
    assert len(r.json()["entries"]) == 1        # 회차가 그대로 남아야 합니다


# ---------------------------------------------------------------- 삭제
def test_사업을_지우면_입력_내역도_함께_지워진다(client):
    pid = client.post(P, json=payload()).json()["id"]
    client.put(f"{P}/{pid}/entries/W2026-08-24", json={"act": "1회차", "baseVersion": 0})

    r = client.request("DELETE", f"{P}/{pid}")
    assert r.status_code == 200
    assert client.get(f"{P}/{pid}").status_code == 404
    assert all(x["id"] != pid for x in client.get(P).json())


def test_다른_사업은_지워지지_않는다(client):
    a = client.post(P, json=payload(name="A")).json()["id"]
    b = client.post(P, json=payload(name="B")).json()["id"]
    client.request("DELETE", f"{P}/{a}")
    assert client.get(f"{P}/{b}").status_code == 200


# ---------------------------------------------------------------- 매뉴얼 주소
def test_매뉴얼_주소를_저장한다(client):
    r = client.patch("/api/settings/manual-url", json={"url": "www.notion.so/abc"})
    assert r.json()["url"] == "https://www.notion.so/abc"      # http 가 없으면 붙여 줍니다
    assert client.get("/api/settings").json()["manual_url"]["url"] == "https://www.notion.so/abc"


def test_성과지표_목표는_소수점을_허용한다(client):
    """'만족도 4.5점' 같은 목표가 실제로 있습니다. 프로토타입도 허용했습니다."""
    r = client.post(P, json=payload(kpis=[{"name": "환자 만족도", "target": 4.5, "unit": "점"}]))
    assert r.status_code == 200, r.text
    assert r.json()["kpis"][0]["target"] == 4.5
