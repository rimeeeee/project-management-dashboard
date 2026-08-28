"""테스트는 임시 데이터베이스에서 돌립니다. 개발용 데이터를 건드리지 않습니다."""
from __future__ import annotations

import os
import tempfile
from datetime import date
from pathlib import Path

import pytest

_tmp = Path(tempfile.mkdtemp(prefix="bizdash-test-"))
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_tmp}/test.db"
os.environ["APP_PASSWORD_HASH"] = ""      # 개발용 기본 비밀번호로 로그인
os.environ["SECRET_KEY"] = "test-only-key"

from fastapi.testclient import TestClient        # noqa: E402
from urllib.parse import quote                   # noqa: E402

from app.db.session import Base, SessionLocal, engine   # noqa: E402
from app.main import app                                # noqa: E402
from app.models import (                                # noqa: E402
    Project, ProjectCategory, ProjectKpi, ProjectStageNote, ProjectTask,
)


@pytest.fixture()
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    s = SessionLocal()
    p = Project(
        id="t1", name="테스트 사업", agency="보건복지부",
        start=date(2026, 6, 1), end=date(2027, 5, 31),
        budget=1_000_000_000, cycle="주간", stage=1,
    )
    p.categories += [ProjectCategory(name="인건비", budget_amount=400_000_000, sort_order=0),
                     ProjectCategory(name="여비", budget_amount=100_000_000, sort_order=1)]
    p.tasks += [ProjectTask(name="과제 A", done=True, sort_order=0),
                ProjectTask(name="과제 B", done=False, sort_order=1)]
    p.kpis += [ProjectKpi(name="논문", unit="건", target=4, sort_order=0)]
    p.stage_notes += [ProjectStageNote(stage_index=i, note="") for i in range(5)]
    s.add(p)
    s.commit()
    yield s
    s.close()


@pytest.fixture()
def client(db):
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"password": "bizdash2026"})
    assert r.status_code == 200, r.text
    return c


def who(name: str) -> dict[str, str]:
    """입력자 이름을 화면(encodeURIComponent)과 같은 방식으로 담습니다."""
    return {"X-Entered-By": quote(name)}
