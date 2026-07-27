"""Replace customizable sites with one fixed business template.

Revision ID: 20260725_0002
Revises: 20260721_0001
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260725_0002"
down_revision: str | Sequence[str] | None = "20260721_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    site_columns = (
        {column["name"] for column in inspector.get_columns("business_sites")}
        if "business_sites" in tables
        else set()
    )

    if "business_sites" in tables and "hero_image_url" not in site_columns:
        op.add_column("business_sites", sa.Column("hero_image_url", sa.Text(), nullable=True))
    if "business_sites" in tables and "logo_url" not in site_columns:
        op.add_column("business_sites", sa.Column("logo_url", sa.Text(), nullable=True))

    if "business_sites" in tables and "favicon_url" in site_columns:
        op.execute(
            sa.text(
                "UPDATE business_sites SET logo_url = favicon_url "
                "WHERE logo_url IS NULL AND favicon_url IS NOT NULL"
            )
        )

    if "site_sections" in tables:
        op.execute(
            sa.text(
                """
                UPDATE business_sites AS site
                SET hero_image_url = hero.content->>'image_url'
                FROM (
                    SELECT DISTINCT ON (site_id) site_id, content
                    FROM site_sections
                    WHERE section_type = 'hero'
                    ORDER BY site_id, position
                ) AS hero
                WHERE site.id = hero.site_id
                  AND site.hero_image_url IS NULL
                  AND hero.content ? 'image_url'
                """
            )
        )
        op.drop_table("site_sections")

    if "business_sites" in tables:
        if "template_id" in site_columns:
            op.drop_constraint(
                "business_sites_template_id_fkey", "business_sites", type_="foreignkey"
            )
        for column_name in (
            "template_id",
            "favicon_url",
            "seo",
            "palette",
            "typography",
            "is_published",
        ):
            if column_name in site_columns:
                op.drop_column("business_sites", column_name)

    if "site_templates" in tables:
        op.drop_table("site_templates")


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "site_templates" not in tables:
        op.create_table(
            "site_templates",
            sa.Column("name", sa.String(length=100), nullable=False, unique=True),
            sa.Column(
                "recommended_business_types",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column(
                "config",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
            sa.PrimaryKeyConstraint("id"),
        )

    columns = {column["name"] for column in sa.inspect(bind).get_columns("business_sites")}
    if "template_id" not in columns:
        op.add_column("business_sites", sa.Column("template_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            "business_sites_template_id_fkey",
            "business_sites",
            "site_templates",
            ["template_id"],
            ["id"],
        )
    if "favicon_url" not in columns:
        op.add_column("business_sites", sa.Column("favicon_url", sa.Text(), nullable=True))
    for column_name in ("seo", "palette", "typography"):
        if column_name not in columns:
            op.add_column(
                "business_sites",
                sa.Column(
                    column_name,
                    postgresql.JSONB(),
                    nullable=False,
                    server_default=sa.text("'{}'::jsonb"),
                ),
            )
    if "is_published" not in columns:
        op.add_column(
            "business_sites",
            sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    op.execute(
        sa.text(
            "UPDATE business_sites SET favicon_url = logo_url "
            "WHERE favicon_url IS NULL AND logo_url IS NOT NULL"
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE business_sites AS site
            SET is_published = business.is_published
            FROM businesses AS business
            WHERE business.id = site.business_id
            """
        )
    )

    if "site_sections" not in tables:
        op.create_table(
            "site_sections",
            sa.Column("site_id", sa.Uuid(), nullable=False),
            sa.Column("section_type", sa.String(length=20), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("content", postgresql.JSONB(), nullable=False),
            sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
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
            sa.ForeignKeyConstraint(["site_id"], ["business_sites.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("site_id", "position"),
        )
        op.create_index("ix_site_sections_site_id", "site_sections", ["site_id"])

    for column_name in ("hero_image_url", "logo_url"):
        if column_name in columns:
            op.drop_column("business_sites", column_name)
