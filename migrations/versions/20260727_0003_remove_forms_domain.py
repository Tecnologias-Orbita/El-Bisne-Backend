"""Remove the forms domain tables.

Revision ID: 20260727_0003
Revises: 20260725_0002
Create Date: 2026-07-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260727_0003"
down_revision: str | Sequence[str] | None = "20260725_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS form_submissions")
    op.execute("DROP TABLE IF EXISTS form_fields")
    op.execute("DROP TABLE IF EXISTS forms")


def downgrade() -> None:
    raise NotImplementedError("The removed forms domain cannot be restored automatically")
