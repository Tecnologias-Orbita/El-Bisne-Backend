import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.shared.infrastructure.models import TimestampMixin, UUIDPrimaryKeyMixin


class SiteTemplateModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "site_templates"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    recommended_business_types: Mapped[list[str]] = mapped_column(JSONB, default=list)
    config: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class BusinessSiteModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "business_sites"

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), unique=True
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("site_templates.id"))
    favicon_url: Mapped[str | None] = mapped_column(Text)
    seo: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    palette: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    typography: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)


class SiteSectionModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "site_sections"
    __table_args__ = (UniqueConstraint("site_id", "position"),)

    site_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_sites.id", ondelete="CASCADE"), index=True
    )
    section_type: Mapped[str] = mapped_column(String(20))
    position: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict[str, object]] = mapped_column(JSONB)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
