import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.application.dto.billing import (
    ExchangeRateDTO,
    PlatformPaymentSettingsDTO,
    SubscriptionPaymentDTO,
)
from app.modules.billing.application.services import require_platform_admin
from app.modules.billing.domain.plans import SubscriptionPlan
from app.modules.billing.infrastructure.models.billing import (
    ExchangeRateModel,
    PlatformPaymentSettingsModel,
    SubscriptionPaymentModel,
)
from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
)
from app.modules.businesses.infrastructure.models.business import BusinessModel
from app.shared.domain.exceptions import ForbiddenError, NotFoundError


@dataclass(frozen=True)
class GetPlatformPaymentSettings:
    pass


@dataclass(frozen=True)
class ListExchangeRates:
    pass


@dataclass(frozen=True)
class ListBusinessSubscriptionPayments:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    payment_id: uuid.UUID | None = None
    transaction_number: str | None = None
    plan: SubscriptionPlan | None = None
    phone_number: str | None = None
    execution_date: date | None = None
    expiration_date: date | None = None
    amount_paid: Decimal | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class ListAllSubscriptionPayments:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID | None = None
    payment_id: uuid.UUID | None = None
    business_name: str | None = None
    transaction_number: str | None = None
    plan: SubscriptionPlan | None = None
    phone_number: str | None = None
    execution_date: date | None = None
    expiration_date: date | None = None
    amount_paid: Decimal | None = None
    created_at: datetime | None = None


def _payment_dto(payment: SubscriptionPaymentModel) -> SubscriptionPaymentDTO:
    return SubscriptionPaymentDTO(
        payment.id,
        payment.business_id,
        payment.transaction_number,
        payment.plan,
        payment.phone_number,
        payment.execution_date,
        payment.expiration_date,
        payment.amount_paid,
        payment.created_at,
    )


def _apply_payment_filters(statement, query):
    if query.payment_id is not None:
        statement = statement.where(SubscriptionPaymentModel.id == query.payment_id)
    if query.transaction_number:
        statement = statement.where(
            SubscriptionPaymentModel.transaction_number.ilike(
                f"%{query.transaction_number.strip()}%"
            )
        )
    if query.plan is not None:
        statement = statement.where(SubscriptionPaymentModel.plan == query.plan)
    if query.phone_number:
        statement = statement.where(
            SubscriptionPaymentModel.phone_number.ilike(f"%{query.phone_number.strip()}%")
        )
    if query.execution_date is not None:
        statement = statement.where(SubscriptionPaymentModel.execution_date == query.execution_date)
    if query.expiration_date is not None:
        statement = statement.where(
            SubscriptionPaymentModel.expiration_date == query.expiration_date
        )
    if query.amount_paid is not None:
        statement = statement.where(SubscriptionPaymentModel.amount_paid == query.amount_paid)
    if query.created_at is not None:
        statement = statement.where(SubscriptionPaymentModel.created_at == query.created_at)
    return statement


class GetPlatformPaymentSettingsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, _: GetPlatformPaymentSettings) -> PlatformPaymentSettingsDTO:
        settings = await self.session.get(PlatformPaymentSettingsModel, 1)
        if settings is None:
            raise NotFoundError("Platform payment settings have not been configured")
        return PlatformPaymentSettingsDTO(settings.bank_card, settings.confirmation_phone_number)


class ListExchangeRatesHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, _: ListExchangeRates) -> list[ExchangeRateDTO]:
        rates = await self.session.scalars(
            select(ExchangeRateModel).order_by(ExchangeRateModel.currency)
        )
        return [ExchangeRateDTO(x.id, x.currency, x.value_in_cup) for x in rates]


class ListBusinessSubscriptionPaymentsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(
        self, query: ListBusinessSubscriptionPayments
    ) -> list[SubscriptionPaymentDTO]:
        authorization = BusinessAuthorizationService(self.session)
        role = (
            "platform_admin"
            if await authorization.is_platform_admin(query.actor_user_id)
            else await authorization.get_role(query.actor_user_id, query.business_id)
        )
        if role not in {"owner", "platform_admin"}:
            raise ForbiddenError("Only the business owner can view subscription payments")
        statement = select(SubscriptionPaymentModel).where(
            SubscriptionPaymentModel.business_id == query.business_id
        )
        statement = _apply_payment_filters(statement, query)
        payments = await self.session.scalars(
            statement.order_by(SubscriptionPaymentModel.execution_date.desc())
        )
        return [_payment_dto(x) for x in payments]


class ListAllSubscriptionPaymentsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: ListAllSubscriptionPayments) -> list[SubscriptionPaymentDTO]:
        await require_platform_admin(self.session, query.actor_user_id)
        statement = select(SubscriptionPaymentModel)
        if query.business_name:
            statement = statement.join(
                BusinessModel, BusinessModel.id == SubscriptionPaymentModel.business_id
            ).where(BusinessModel.name.ilike(f"%{query.business_name.strip()}%"))
        if query.business_id is not None:
            statement = statement.where(SubscriptionPaymentModel.business_id == query.business_id)
        statement = _apply_payment_filters(statement, query)
        payments = await self.session.scalars(
            statement.order_by(SubscriptionPaymentModel.execution_date.desc())
        )
        return [_payment_dto(x) for x in payments]
