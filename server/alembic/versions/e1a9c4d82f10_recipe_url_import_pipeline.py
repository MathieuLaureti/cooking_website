"""recipe url import pipeline fields

Revision ID: e1a9c4d82f10
Revises: c7e1b4a92d10
Create Date: 2026-09-27 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e1a9c4d82f10"
down_revision: Union[str, Sequence[str], None] = "c7e1b4a92d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recipe_url_import", sa.Column("page_text", sa.Text(), nullable=True))
    op.add_column(
        "recipe_url_import",
        sa.Column("structured_ingredients", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("recipe_url_import", sa.Column("pipeline_step", sa.SmallInteger(), nullable=True))
    op.add_column(
        "recipe_url_import",
        sa.Column("ai_attempt_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "recipe_url_import",
        sa.Column("ai_next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_index("uq_recipe_url_import_active", table_name="recipe_url_import")
    op.create_index(
        "uq_recipe_url_import_active",
        "recipe_url_import",
        ["normalized_url"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running', 'ready', 'ai_wait')"),
    )


def downgrade() -> None:
    op.drop_index("uq_recipe_url_import_active", table_name="recipe_url_import")
    op.create_index(
        "uq_recipe_url_import_active",
        "recipe_url_import",
        ["normalized_url"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running', 'ready')"),
    )
    op.drop_column("recipe_url_import", "ai_next_attempt_at")
    op.drop_column("recipe_url_import", "ai_attempt_count")
    op.drop_column("recipe_url_import", "pipeline_step")
    op.drop_column("recipe_url_import", "structured_ingredients")
    op.drop_column("recipe_url_import", "page_text")
