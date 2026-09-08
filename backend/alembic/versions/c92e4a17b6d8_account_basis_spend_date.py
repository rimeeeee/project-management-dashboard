"""budget: account, basis, spend date

  - projects.account          : 계정과목 (사업마다 하나)
  - project_categories.basis  : 편성액 산출 근거 쪽지
  - entry_spends.spend_on     : 실제 지출일 (월별 합산의 기준)

Revision ID: c92e4a17b6d8
Revises: b41c7f2a9e30
Create Date: 2026-09-09
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = 'c92e4a17b6d8'
down_revision = 'b41c7f2a9e30'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('projects',
                  sa.Column('account', sa.String(length=80), nullable=False, server_default=''))
    op.add_column('project_categories',
                  sa.Column('basis', sa.Text(), nullable=False, server_default=''))
    # 지출일은 비워 둘 수 있습니다. 비면 회차 날짜로 봅니다.
    op.add_column('entry_spends', sa.Column('spend_on', sa.Date(), nullable=True))

    # 이미 넣어 둔 집행 내역은 회차 날짜로 채웁니다. 비워 두면 화면에서
    # 지출일 칸이 모두 빈 채로 보여, 안 적은 것인지 원래 없던 것인지
    # 구분이 안 됩니다.
    op.execute("""
        UPDATE entry_spends
           SET spend_on = (SELECT entry_date FROM report_entries
                            WHERE report_entries.id = entry_spends.entry_id)
         WHERE spend_on IS NULL
    """)

    # 채우기가 끝났으니 기본값은 떼어 냅니다 — 앞으로는 코드가 값을 정합니다.
    # SQLite 는 ALTER COLUMN 을 못 해서 개발용에서는 그대로 둡니다.
    # 값이 빈 문자열이라 남아 있어도 해가 없습니다.
    if op.get_bind().dialect.name != 'sqlite':
        op.alter_column('projects', 'account', server_default=None)
        op.alter_column('project_categories', 'basis', server_default=None)


def downgrade() -> None:
    op.drop_column('entry_spends', 'spend_on')
    op.drop_column('project_categories', 'basis')
    op.drop_column('projects', 'account')
