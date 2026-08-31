"""
프로토타입 예시 사업을 지웁니다.

    .venv/bin/python scripts/seed/clear_examples.py

'연구중심병원 육성(R&D) 협력지원 과제' 와 '스마트병원 선도모델 지원사업' 은
프로토타입에 들어 있던 예시입니다. 화면을 만들고 확인하는 동안 필요했지만
실제로 쓰기 시작할 때는 없어야 합니다.

공고는 지우지 않습니다. 실제로 수집한 자료입니다.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import SessionLocal          # noqa: E402
from app.models import Announcement, Project     # noqa: E402

EXAMPLE_IDS = ("p1", "p2")


def main() -> int:
    db = SessionLocal()
    try:
        rows = [p for p in db.query(Project).all() if p.id in EXAMPLE_IDS]
        if not rows:
            print("지울 예시 사업이 없습니다. (이미 정리된 상태입니다)")
        for p in rows:
            print(f"  지움: {p.name}  (회차 {len(p.entries)}건 함께)")
            db.delete(p)
        db.commit()

        left = db.query(Project).count()
        print(f"\n남은 사업 {left}건 · 공고 {db.query(Announcement).count()}건(그대로 둡니다)")
        if left == 0:
            print("\n이제 화면에서 [신규 사업 등록] 으로 실제 사업을 넣으시면 됩니다.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
