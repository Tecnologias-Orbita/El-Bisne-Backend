"""Replace business and product types with online sales and services.

Revision ID: 20260807_0007
Revises: 20260728_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260807_0007"
down_revision: str | Sequence[str] | None = "20260728_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column("sells_online", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.drop_column("businesses", "business_type")
    op.drop_column("products", "product_type")
    op.create_table(
        "services",
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("platform_category_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(
            ["platform_category_id"], ["platform_categories.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "slug"),
    )
    op.create_index("ix_services_business_id", "services", ["business_id"])
    op.create_index("ix_services_platform_category_id", "services", ["platform_category_id"])


def downgrade() -> None:
    op.drop_index("ix_services_platform_category_id", table_name="services")
    op.drop_index("ix_services_business_id", table_name="services")
    op.drop_table("services")
    op.add_column(
        "products",
        sa.Column("product_type", sa.String(20), server_default="product", nullable=False),
    )
    op.add_column(
        "businesses",
        sa.Column("business_type", sa.String(50), server_default="business", nullable=False),
    )
    op.drop_column("businesses", "sells_online")
