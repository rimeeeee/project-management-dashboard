"""meeting: time, writer, next steps

회의록 양식에 있으나 받지 못하던 세 칸을 채웁니다.
  - 시간(시작·끝)      : 감사에서 회의 시간대를 확인합니다
  - 작성자
  - 요청 및 예정 사항  : 회의내용에서 이어지는 할 일

Revision ID: b41c7f2a9e30
Revises: ed0b89894a75
Create Date: 2026-09-08
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = 'b41c7f2a9e30'
down_revision = 'ed0b89894a75'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 이미 쌓인 회의록에도 값이 있어야 하므로 server_default 로 빈 값을 채웁니다.
    # 채우고 나면 기본값은 떼어 냅니다 — 앞으로는 코드가 값을 정합니다.
    op.add_column('meetings', sa.Column('met_start', sa.String(length=5),
                                        nullable=False, server_default=''))
    op.add_column('meetings', sa.Column('met_end', sa.String(length=5),
                                        nullable=False, server_default=''))
    op.add_column('meetings', sa.Column('writer', sa.String(length=60),
                                        nullable=False, server_default=''))
    op.add_column('meetings', sa.Column('next_steps', sa.JSON(),
                                        nullable=False, server_default='[]'))
    # 기본값을 떼어 냅니다 — 채우기가 끝났으니 앞으로는 코드가 값을 정합니다.
    # SQLite 는 ALTER COLUMN 을 못 합니다. 여기서 표를 통째로 다시 만들면
    # 얻는 것에 비해 위험이 커서, 개발용 SQLite 에서는 기본값을 그대로 둡니다.
    # 값이 빈 문자열·빈 목록이라 남아 있어도 해가 없습니다.
    if op.get_bind().dialect.name != 'sqlite':
        for col in ('met_start', 'met_end', 'writer', 'next_steps'):
            op.alter_column('meetings', col, server_default=None)


def downgrade() -> None:
    for col in ('next_steps', 'writer', 'met_end', 'met_start'):
        op.drop_column('meetings', col)
