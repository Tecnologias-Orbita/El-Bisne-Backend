import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.shared.infrastructure.models import TimestampMixin, UUIDPrimaryKeyMixin


class AnalyticsEventModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "analytics_events"

    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(40))
    resource_id: Mapped[uuid.UUID | None]
    anonymous_reference: Mapped[str | None] = mapped_column(String(64))
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, default=dict)
