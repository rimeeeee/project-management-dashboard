"""add stage to project_tasks

추진 과제가 어느 단계 것인지 담습니다 (0 기획 · 1 착수 · 2 진행 · 3 마무리 · 4 완료).
단계별로 몇 건이 끝났는지 보여 주기 위한 것이고, 전체 진행률 계산은 바뀌지 않습니다
(예나 지금이나 완료 과제 ÷ 전체 과제).

Revision ID: 6e293e9d290c
Revises: 7873989df1fe
Create Date: 2026-09-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '6e293e9d290c'
down_revision = '7873989df1fe'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 이미 자료가 있는 서버에서도 돌아야 하므로 기본값을 주고 넣습니다.
    # 기본값 없이 NOT NULL 을 붙이면 기존 줄에 채울 값이 없어 실패합니다.
    with op.batch_alter_table('project_tasks', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('stage', sa.Integer(), nullable=False, server_default='2')
        )

    # 이미 있던 과제에 단계를 나눠 넣습니다.
    # 과제는 sort_order 로 이미 진행 순서대로 놓여 있으므로, 그 순서를
    # 착수~완료(1~4)에 고르게 나눕니다. 기획은 대개 과제를 만들기 전에
    # 끝나 있어 비워 둡니다.
    # 기계적인 배분이라 실제와 다를 수 있습니다. 화면에서 고치면 됩니다.
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, project_id, sort_order FROM project_tasks "
                "ORDER BY project_id, sort_order, id")
    ).fetchall()

    묶음: dict[str, list[int]] = {}
    for task_id, project_id, _ in rows:
        묶음.setdefault(project_id, []).append(task_id)

    for task_ids in 묶음.values():
        n = len(task_ids)
        for i, task_id in enumerate(task_ids):
            단계 = min(4, 1 + (i * 4) // n)
            conn.execute(
                sa.text("UPDATE project_tasks SET stage = :s WHERE id = :i"),
                {"s": 단계, "i": task_id},
            )


def downgrade() -> None:
    with op.batch_alter_table('project_tasks', schema=None) as batch_op:
        batch_op.drop_column('stage')
