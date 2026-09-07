"""split category budget into gov and self

비목별 배정액을 국고보조금과 자기부담금으로 나눠 받습니다.
budget_amount 는 그대로 두 값의 합이고, 집행률·잔액 같은 화면 숫자는
예나 지금이나 이 합계만 씁니다.

Revision ID: cac0640bbf29
Revises: 6e293e9d290c
Create Date: 2026-09-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = 'cac0640bbf29'
down_revision = '6e293e9d290c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 이미 자료가 있는 서버에서도 돌아야 하므로 기본값을 주고 넣습니다.
    with op.batch_alter_table('project_categories', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('budget_gov', sa.BigInteger(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column('budget_self', sa.BigInteger(), nullable=False, server_default='0')
        )

    # 이미 있던 비목은 나눈 정보가 없습니다. 합계가 어긋나면 안 되므로
    # 전액을 국고보조금으로 넣어 둡니다(gov + self = budget_amount 를 지킵니다).
    # 실제로 자기부담금이 있는 비목은 사업 등록 화면에서 고치면 됩니다.
    op.execute(sa.text(
        "UPDATE project_categories SET budget_gov = budget_amount, budget_self = 0"
    ))


def downgrade() -> None:
    with op.batch_alter_table('project_categories', schema=None) as batch_op:
        batch_op.drop_column('budget_self')
        batch_op.drop_column('budget_gov')
