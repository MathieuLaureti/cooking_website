"""add recipe url import queue

Revision ID: c7e1b4a92d10
Revises: b3d8a1c64e20
Create Date: 2026-09-26 08:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c7e1b4a92d10"
down_revision: Union[str, Sequence[str], None] = "b3d8a1c64e20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recipe_url_import",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("normalized_url", sa.String(length=2048), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="queued", nullable=False),
        sa.Column("extract", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("recipe_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipe.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_recipe_url_import_active",
        "recipe_url_import",
        ["normalized_url"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running', 'ready')"),
    )


def downgrade() -> None:
    op.drop_index("uq_recipe_url_import_active", table_name="recipe_url_import")
    op.drop_table("recipe_url_import")
