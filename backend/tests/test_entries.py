"""
보고 회차 저장 — 프로토타입에서 가장 크게 달라지는 부분이라 촘촘히 확인합니다.

프로토타입은 저장할 때 전체 데이터를 통째로 덮어썼습니다.
여기서 확인하려는 것은 두 가지입니다.
  1) 저장이 '그 회차 한 줄'만 건드리는가
  2) 두 사람이 같은 회차를 동시에 고칠 때 조용히 덮어쓰지 않는가
"""
from __future__ import annotations

from datetime import date

P = "/api/projects/t1"
WEEK = "W2026-08-24"      # 8월 4주차
OTHER = "W2026-08-17"     # 8월 3주차


def body(**kw):
    base = {"spends": [], "kpi": {}, "act": "", "issue": "", "plan": "", "baseVersion": 0}
    base.update(kw)
    return base


# ---------------------------------------------------------------- 기본
def test_새_회차를_저장한다(client):
    r = client.put(f"{P}/entries/{WEEK}",
                   json=body(act="첫 입력", spends=[{"cat": "인건비", "amt": 5_000_000}]))
    assert r.status_code == 200, r.text
    e = r.json()["entry"]
    assert e["version"] == 1
    assert e["spendTotal"] == 5_000_000
    assert e["act"] == "첫 입력"


# ---------------------------------------------------------------- 회차별 저장
def test_한_회차를_저장해도_다른_회차는_그대로다(client):
    client.put(f"{P}/entries/{OTHER}",
               json=body(act="3주차", spends=[{"cat": "여비", "amt": 1_000_000}]))
    client.put(f"{P}/entries/{WEEK}",
               json=body(act="4주차", spends=[{"cat": "인건비", "amt": 2_000_000}]))

    entries = {e["periodKey"]: e for e in client.get(P).json()["entries"]}
    assert entries[OTHER]["act"] == "3주차"
    assert entries[OTHER]["spendTotal"] == 1_000_000
    assert entries[WEEK]["act"] == "4주차"
    assert entries[WEEK]["spendTotal"] == 2_000_000


def test_금액이_0인_집행줄은_버린다(client):
    r = client.put(f"{P}/entries/{WEEK}",
                   json=body(spends=[{"cat": "인건비", "amt": 0},
                                     {"cat": "여비", "amt": 3_000_000}]))
    assert len(r.json()["entry"]["spends"]) == 1


def test_음수_집행액은_막는다(client):
    r = client.put(f"{P}/entries/{WEEK}",
                   json=body(spends=[{"cat": "인건비", "amt": -1}]))
    assert r.status_code == 400


# ---------------------------------------------------------------- 동시 저장
def test_이미_있는_회차를_신규로_저장하면_알려준다(client):
    client.put(f"{P}/entries/{WEEK}", json=body(act="먼저"))
    r = client.put(f"{P}/entries/{WEEK}", json=body(act="나중"))
    assert r.status_code == 409
    assert r.json()["kind"] == "exists"
    # 덮어쓰지 않았는지 확인
    assert client.get(P).json()["entries"][0]["act"] == "먼저"


def test_같은_회차를_동시에_고치면_나중_저장이_먼저_것을_지우지_않는다(client):
    client.put(f"{P}/entries/{WEEK}", json=body(act="처음"))

    # 두 사람이 같은 화면(v1)을 보고 있습니다
    r1 = client.put(f"{P}/entries/{WEEK}", json=body(act="박팀장 수정", baseVersion=1))
    assert r1.status_code == 200
    assert r1.json()["entry"]["version"] == 2

    r2 = client.put(f"{P}/entries/{WEEK}", json=body(act="김담당 수정", baseVersion=1))
    assert r2.status_code == 409
    d = r2.json()
    assert d["kind"] == "conflict"
    assert d["current"]["act"] == "박팀장 수정"

    # 박팀장의 저장이 살아 있어야 합니다
    assert client.get(P).json()["entries"][0]["act"] == "박팀장 수정"


def test_최신_번호로_다시_보내면_저장된다(client):
    client.put(f"{P}/entries/{WEEK}", json=body(act="처음"))
    client.put(f"{P}/entries/{WEEK}", json=body(act="두번째", baseVersion=1))
    r = client.put(f"{P}/entries/{WEEK}", json=body(act="세번째", baseVersion=2))
    assert r.status_code == 200
    assert r.json()["entry"]["act"] == "세번째"


# ---------------------------------------------------------------- 이력
def test_고치기_전_내용이_이력으로_남는다(client):
    client.put(f"{P}/entries/{WEEK}", json=body(act="처음", spends=[{"cat": "인건비", "amt": 1_000_000}]))
    client.put(f"{P}/entries/{WEEK}", json=body(act="고침", baseVersion=1))

    h = client.get(f"{P}/entries/{WEEK}/history").json()
    assert len(h) == 1
    assert h[0]["action"] == "update"
    assert h[0]["snapshot"]["act"] == "처음"           # 바뀌기 전 내용
    assert h[0]["snapshot"]["spendTotal"] == 1_000_000


def test_회차를_지워도_누가_지웠는지_남는다(client):
    client.put(f"{P}/entries/{WEEK}", json=body(act="지울 내용"))
    r = client.request("DELETE", f"{P}/entries/{WEEK}")
    assert r.status_code == 200
    assert r.json()["project"]["entries"] == []

    h = client.get(f"{P}/entries/{WEEK}/history").json()
    assert h[0]["action"] == "delete"
    assert h[0]["snapshot"]["act"] == "지울 내용"


def test_회차를_지워도_그_전_수정이력이_남는다(client):
    """
    회차를 지울 때 이력까지 함께 지워지면, 정작 '누가 언제 무엇을 지웠는지'가
    가장 중요한 경우에 확인할 방법이 없어집니다. 실제로 한 번 그렇게 지워졌습니다.
    """
    client.put(f"{P}/entries/{WEEK}", json=body(act="처음"))
    client.put(f"{P}/entries/{WEEK}", json=body(act="두번째", baseVersion=1))
    client.put(f"{P}/entries/{WEEK}", json=body(act="세번째", baseVersion=2))
    client.request("DELETE", f"{P}/entries/{WEEK}")

    h = client.get(f"{P}/entries/{WEEK}/history").json()
    actions = [r["action"] for r in h]
    assert actions == ["delete", "update", "update"], actions
    # 지우기 전 마지막 내용과, 그 전 내용들이 모두 남아 있어야 합니다
    assert h[0]["snapshot"]["act"] == "세번째"
    assert h[1]["snapshot"]["act"] == "두번째"
    assert h[2]["snapshot"]["act"] == "처음"


# ---------------------------------------------------------------- 확인사항
def test_확인사항_해결_표시를_켜고_끈다(client):
    client.put(f"{P}/entries/{WEEK}", json=body(issue="장비 납품 지연", plan="분할 납품"))
    # 미해결 확인사항이 있으면 상태가 '점검 필요'가 되어야 합니다
    assert client.get(P).json()["status"]["label"] == "점검 필요"

    client.post(f"{P}/entries/{WEEK}/issue-toggle")
    d = client.get(P).json()
    assert d["entries"][0]["issueDone"] is True
    assert d["status"]["label"] != "점검 필요"


def test_확인사항_내용을_지우면_해결표시도_함께_지운다(client):
    client.put(f"{P}/entries/{WEEK}", json=body(issue="문제"))
    client.post(f"{P}/entries/{WEEK}/issue-toggle")
    v = client.get(P).json()["entries"][0]["version"]
    client.put(f"{P}/entries/{WEEK}", json=body(issue="", baseVersion=v))
    assert client.get(P).json()["entries"][0]["issueDone"] is False


# ---------------------------------------------------------------- 즉시 저장
def test_추진과제_체크가_진행률에_바로_반영된다(client):
    assert client.get(P).json()["actual"] == 50        # 2건 중 1건 완료
    client.patch(f"{P}/task", json={"index": 1, "done": True})
    assert client.get(P).json()["actual"] == 100


def test_진행단계와_단계별_내용을_저장한다(client):
    client.patch(f"{P}/stage", json={"stage": 3})
    client.patch(f"{P}/stage-note", json={"index": 3, "note": "마무리 진행 중"})
    d = client.get(P).json()
    assert d["stage"] == 3
    assert d["stageNotes"][3] == "마무리 진행 중"


def test_할_일을_추가하고_완료하고_지운다(client):
    r = client.post(f"{P}/todos", json={"text": "보고서 작성", "due": "2026-09-04"})
    todo = r.json()["todos"][0]
    assert todo["text"] == "보고서 작성" and todo["done"] is False

    r = client.patch(f"{P}/todos/{todo['id']}")
    assert r.json()["todos"][0]["done"] is True

    r = client.request("DELETE", f"{P}/todos/{todo['id']}")
    assert r.json()["todos"] == []


# ---------------------------------------------------------------- 로그인
def test_로그인하지_않으면_저장할_수_없다(db):
    from fastapi.testclient import TestClient

    from app.main import app

    anon = TestClient(app)
    r = anon.put(f"{P}/entries/{WEEK}", json=body(act="x"))
    assert r.status_code == 401
