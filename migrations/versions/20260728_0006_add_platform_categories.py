"""Add platform categories and optional business and product links.

Revision ID: 20260728_0006
Revises: 20260728_0005
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0006"
down_revision: str | Sequence[str] | None = "20260728_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_categories",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_platform_categories_slug", "platform_categories", ["slug"], unique=True)
    op.create_index("ix_platform_categories_is_active", "platform_categories", ["is_active"])
    op.add_column("businesses", sa.Column("platform_category_id", sa.Uuid(), nullable=True))
    op.create_index("ix_businesses_platform_category_id", "businesses", ["platform_category_id"])
    op.create_foreign_key(
        "fk_businesses_platform_category",
        "businesses",
        "platform_categories",
        ["platform_category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("products", sa.Column("platform_category_id", sa.Uuid(), nullable=True))
    op.create_index("ix_products_platform_category_id", "products", ["platform_category_id"])
    op.create_foreign_key(
        "fk_products_platform_category",
        "products",
        "platform_categories",
        ["platform_category_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_products_platform_category", "products", type_="foreignkey")
    op.drop_index("ix_products_platform_category_id", table_name="products")
    op.drop_column("products", "platform_category_id")
    op.drop_constraint("fk_businesses_platform_category", "businesses", type_="foreignkey")
    op.drop_index("ix_businesses_platform_category_id", table_name="businesses")
    op.drop_column("businesses", "platform_category_id")
    op.drop_index("ix_platform_categories_is_active", table_name="platform_categories")
    op.drop_index("ix_platform_categories_slug", table_name="platform_categories")
    op.drop_table("platform_categories")
