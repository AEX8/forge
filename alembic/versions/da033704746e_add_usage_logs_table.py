"""add usage_logs table

Revision ID: da033704746e
Revises: 0ac1f1115bf6
Create Date: 2026-09-10 21:00:07.941521

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da033704746e'
down_revision: Union[str, None] = '0ac1f1115bf6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('usage_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('request_id', sa.UUID(), nullable=True),
    sa.Column('api_key_id', sa.UUID(), nullable=False),
    sa.Column('model_used', sa.String(), nullable=True),
    sa.Column('tokens_in', sa.Integer(), nullable=True),
    sa.Column('tokens_out', sa.Integer(), nullable=True),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('status_code', sa.Integer(), nullable=False),
    sa.Column('flagged', sa.Boolean(), nullable=True),
    sa.Column('flagged_reason', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usage_logs_request_id'), 'usage_logs', ['request_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_usage_logs_request_id'), table_name='usage_logs')
    op.drop_table('usage_logs')