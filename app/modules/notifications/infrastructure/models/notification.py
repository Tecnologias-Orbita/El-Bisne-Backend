import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.shared.infrastructure.models import TimestampMixin, UUIDPrimaryKeyMixin


class OutboxEventModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "outbox_events"

    event_type: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class NotificationDeliveryModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_deliveries"

    outbox_event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("outbox_events.id"))
    recipient: Mapped[str] = mapped_column(String(320))
    provider: Mapped[str] = mapped_column(String(40), default="email")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
