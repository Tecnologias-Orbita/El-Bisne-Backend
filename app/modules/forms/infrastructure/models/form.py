import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.shared.infrastructure.models import TimestampMixin, UUIDPrimaryKeyMixin


class FormModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "forms"

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")


class FormFieldModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "form_fields"
    __table_args__ = (UniqueConstraint("form_id", "position"),)

    form_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("forms.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(160))
    field_type: Mapped[str] = mapped_column(String(20))
    position: Mapped[int] = mapped_column(Integer)
    is_required: Mapped[bool] = mapped_column(default=False)
    config: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class FormSubmissionModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "form_submissions"

    form_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("forms.id", ondelete="RESTRICT"), index=True
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="RESTRICT"), index=True
    )
    contact_email: Mapped[str | None] = mapped_column(String(320))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    data: Mapped[dict[str, object]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="new")
