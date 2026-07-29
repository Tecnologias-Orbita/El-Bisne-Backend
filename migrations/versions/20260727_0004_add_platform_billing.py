"""Add platform billing, payment settings, and exchange rates.

Revision ID: 20260727_0004
Revises: 20260727_0003
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260727_0004"
down_revision: str | Sequence[str] | None = "20260727_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

subscription_plan = postgresql.ENUM("basic", "premium", name="subscription_plan", create_type=False)


def upgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    billing_tables = {
        "platform_payment_settings",
        "exchange_rates",
        "business_subscription_payments",
    }
    if billing_tables <= existing_tables:
        return
    subscription_plan.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "platform_payment_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_card", sa.String(length=32), nullable=False),
        sa.Column("confirmation_phone_number", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("id = 1", name="ck_platform_payment_settings_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "exchange_rates",
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("value_in_cup", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("value_in_cup > 0", name="ck_exchange_rates_positive_value"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("currency", name="uq_exchange_rates_currency"),
    )
    op.create_index("ix_exchange_rates_currency", "exchange_rates", ["currency"])
    op.create_table(
        "business_subscription_payments",
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_number", sa.String(length=120), nullable=False),
        sa.Column("plan", subscription_plan, nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_number"),
    )
    op.create_index(
        "ix_business_subscription_payments_business_id",
        "business_subscription_payments",
        ["business_id"],
    )
    op.create_index(
        "ix_business_subscription_payments_transaction_number",
        "business_subscription_payments",
        ["transaction_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_business_subscription_payments_transaction_number",
        table_name="business_subscription_payments",
    )
    op.drop_index(
        "ix_business_subscription_payments_business_id",
        table_name="business_subscription_payments",
    )
    op.drop_table("business_subscription_payments")
    op.drop_index("ix_exchange_rates_currency", table_name="exchange_rates")
    op.drop_table("exchange_rates")
    op.drop_table("platform_payment_settings")
    subscription_plan.drop(op.get_bind(), checkfirst=True)
