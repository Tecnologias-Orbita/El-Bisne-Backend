"""Remove unique constraints duplicated by unique indexes.

Revision ID: 20260826_0008
Revises: 20260807_0007
Create Date: 2026-08-26
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260826_0008"
down_revision: str | Sequence[str] | None = "20260807_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "business_subscription_payments_transaction_number_key",
        "business_subscription_payments",
        type_="unique",
    )
    op.drop_constraint(
        "platform_categories_slug_key",
        "platform_categories",
        type_="unique",
    )


def downgrade() -> None:
    op.create_unique_constraint(
        "platform_categories_slug_key",
        "platform_categories",
        ["slug"],
    )
    op.create_unique_constraint(
        "business_subscription_payments_transaction_number_key",
        "business_subscription_payments",
        ["transaction_number"],
    )
