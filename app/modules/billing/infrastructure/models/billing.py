import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.billing.domain.plans import SubscriptionPlan
from app.shared.infrastructure.models import TimestampMixin, UUIDPrimaryKeyMixin


class SubscriptionPaymentModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "business_subscription_payments"
    __table_args__ = (
        CheckConstraint(
            "expiration_date >= execution_date",
            name="ck_subscription_payments_expiration",
        ),
        CheckConstraint(
            "amount_paid >= 0",
            name="ck_subscription_payments_non_negative_amount",
        ),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="RESTRICT"), index=True
    )
    transaction_number: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    plan: Mapped[SubscriptionPlan] = mapped_column(
        Enum(
            SubscriptionPlan,
            name="subscription_plan",
            values_callable=lambda values: [item.value for item in values],
        )
    )
    phone_number: Mapped[str] = mapped_column(String(32))
    execution_date: Mapped[date] = mapped_column()
    expiration_date: Mapped[date] = mapped_column(index=True)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class PlatformPaymentSettingsModel(TimestampMixin, Base):
    __tablename__ = "platform_payment_settings"
    __table_args__ = (CheckConstraint("id = 1", name="ck_platform_payment_settings_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    bank_card: Mapped[str] = mapped_column(String(32))
    confirmation_phone_number: Mapped[str] = mapped_column(String(32))


class ExchangeRateModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("currency", name="uq_exchange_rates_currency"),
        CheckConstraint("value_in_cup > 0", name="ck_exchange_rates_positive_value"),
    )

    currency: Mapped[str] = mapped_column(String(3), index=True)
    value_in_cup: Mapped[Decimal] = mapped_column(Numeric(18, 6))
