"""Add execution, expiration, and amount to subscription payments.

Revision ID: 20260728_0005
Revises: 20260727_0004
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0005"
down_revision: str | Sequence[str] | None = "20260727_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("business_subscription_payments")}
    expected = {"execution_date", "expiration_date", "amount_paid"}
    if expected <= columns:
        return

    if "execution_date" not in columns:
        op.add_column(
            "business_subscription_payments",
            sa.Column("execution_date", sa.Date(), nullable=True),
        )
    if "expiration_date" not in columns:
        op.add_column(
            "business_subscription_payments",
            sa.Column("expiration_date", sa.Date(), nullable=True),
        )
    if "amount_paid" not in columns:
        op.add_column(
            "business_subscription_payments",
            sa.Column("amount_paid", sa.Numeric(14, 2), nullable=True),
        )

    op.execute(
        sa.text(
            """
            UPDATE business_subscription_payments
            SET execution_date = COALESCE(execution_date, created_at::date),
                expiration_date = COALESCE(expiration_date, created_at::date + 30),
                amount_paid = COALESCE(amount_paid, 0)
            """
        )
    )
    for column_name in expected:
        op.alter_column("business_subscription_payments", column_name, nullable=False)
    op.create_check_constraint(
        "ck_subscription_payments_expiration",
        "business_subscription_payments",
        "expiration_date >= execution_date",
    )
    op.create_check_constraint(
        "ck_subscription_payments_non_negative_amount",
        "business_subscription_payments",
        "amount_paid >= 0",
    )
    op.create_index(
        "ix_business_subscription_payments_expiration_date",
        "business_subscription_payments",
        ["expiration_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_business_subscription_payments_expiration_date",
        table_name="business_subscription_payments",
    )
    op.drop_constraint(
        "ck_subscription_payments_non_negative_amount",
        "business_subscription_payments",
        type_="check",
    )
    op.drop_constraint(
        "ck_subscription_payments_expiration",
        "business_subscription_payments",
        type_="check",
    )
    op.drop_column("business_subscription_payments", "amount_paid")
    op.drop_column("business_subscription_payments", "expiration_date")
    op.drop_column("business_subscription_payments", "execution_date")
