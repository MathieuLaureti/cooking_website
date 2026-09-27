"""add catalog sanity run

Revision ID: f8a2c1d93e04
Revises: e1a9c4d82f10
Create Date: 2026-09-27 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f8a2c1d93e04"
down_revision: Union[str, Sequence[str], None] = "e1a9c4d82f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catalog_sanity_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="queued", nullable=False),
        sa.Column("use_laya", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("total_foods", sa.Integer(), nullable=True),
        sa.Column("pipeline_layer", sa.String(length=32), nullable=True),
        sa.Column("layer_current", sa.Integer(), nullable=True),
        sa.Column("layer_total", sa.Integer(), nullable=True),
        sa.Column("drops_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("result_drops", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("catalog_sanity_run")
