import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.modules.billing.domain.plans import SubscriptionPlan


@dataclass(frozen=True)
class SubscriptionPaymentDTO:
    id: uuid.UUID
    business_id: uuid.UUID
    transaction_number: str
    plan: SubscriptionPlan
    phone_number: str
    execution_date: date
    expiration_date: date
    amount_paid: Decimal
    created_at: datetime


@dataclass(frozen=True)
class PlatformPaymentSettingsDTO:
    bank_card: str
    confirmation_phone_number: str


@dataclass(frozen=True)
class ExchangeRateDTO:
    id: uuid.UUID
    currency: str
    value_in_cup: Decimal
