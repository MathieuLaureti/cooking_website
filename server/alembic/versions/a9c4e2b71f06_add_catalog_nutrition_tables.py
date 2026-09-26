"""add catalog nutrition tables

Revision ID: a9c4e2b71f06
Revises: d4e1f0a2b8c3
Create Date: 2026-09-25 21:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a9c4e2b71f06"
down_revision: Union[str, Sequence[str], None] = "d4e1f0a2b8c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catalog_food",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("external_code", sa.String(length=16), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_fr", sa.String(length=255), nullable=False),
        sa.Column("group_code", sa.String(length=8), nullable=True),
        sa.Column("group_en", sa.String(length=80), nullable=True),
        sa.Column("group_fr", sa.String(length=80), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_code"),
    )
    op.create_table(
        "catalog_nutrient",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("external_code", sa.String(length=16), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_fr", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("decimals", sa.Integer(), nullable=True),
        sa.Column("tagname", sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_code"),
    )
    op.create_table(
        "catalog_food_nutrient",
        sa.Column("food_id", sa.Integer(), nullable=False),
        sa.Column("nutrient_id", sa.Integer(), nullable=False),
        sa.Column("amount_per_100g", sa.Numeric(precision=14, scale=6), nullable=False),
        sa.ForeignKeyConstraint(["food_id"], ["catalog_food.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["nutrient_id"], ["catalog_nutrient.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("food_id", "nutrient_id"),
    )
    op.create_table(
        "catalog_alias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("food_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized", sa.String(length=255), nullable=False),
        sa.Column("locale", sa.String(length=2), nullable=False),
        sa.ForeignKeyConstraint(["food_id"], ["catalog_food.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized"),
    )
    op.create_index("ix_catalog_alias_food_id", "catalog_alias", ["food_id"])


def downgrade() -> None:
    op.drop_index("ix_catalog_alias_food_id", table_name="catalog_alias")
    op.drop_table("catalog_alias")
    op.drop_table("catalog_food_nutrient")
    op.drop_table("catalog_nutrient")
    op.drop_table("catalog_food")
