import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select

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
from app.modules.businesses.infrastructure.models.business import BusinessModel
from app.shared.application.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.domain.exceptions import ConflictError, NotFoundError, ValidationError


@dataclass(frozen=True)
class UpdatePlatformPaymentSettings:
    actor_user_id: uuid.UUID
    bank_card: str
    confirmation_phone_number: str


@dataclass(frozen=True)
class CreateExchangeRate:
    actor_user_id: uuid.UUID
    currency: str
    value_in_cup: Decimal


@dataclass(frozen=True)
class UpdateExchangeRate:
    actor_user_id: uuid.UUID
    rate_id: uuid.UUID
    currency: str
    value_in_cup: Decimal


@dataclass(frozen=True)
class DeleteExchangeRate:
    actor_user_id: uuid.UUID
    rate_id: uuid.UUID


@dataclass(frozen=True)
class CreateSubscriptionPayment:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    transaction_number: str
    plan: SubscriptionPlan
    phone_number: str
    execution_date: date
    expiration_date: date
    amount_paid: Decimal


@dataclass(frozen=True)
class UpdateSubscriptionPayment:
    actor_user_id: uuid.UUID
    payment_id: uuid.UUID
    transaction_number: str
    plan: SubscriptionPlan
    phone_number: str
    execution_date: date
    expiration_date: date
    amount_paid: Decimal


@dataclass(frozen=True)
class DeleteSubscriptionPayment:
    actor_user_id: uuid.UUID
    payment_id: uuid.UUID


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


def _validate_payment_dates_and_amount(
    execution_date: date, expiration_date: date, amount_paid: Decimal
) -> None:
    if expiration_date < execution_date:
        raise ValidationError("Expiration date cannot be earlier than execution date")
    if amount_paid <= 0:
        raise ValidationError("Paid amount must be positive")


class UpdatePlatformPaymentSettingsHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: UpdatePlatformPaymentSettings) -> PlatformPaymentSettingsDTO:
        async with self.uow:
            await require_platform_admin(self.uow.session, command.actor_user_id)
            settings = await self.uow.session.get(PlatformPaymentSettingsModel, 1)
            if settings is None:
                settings = PlatformPaymentSettingsModel(id=1)
                self.uow.session.add(settings)
            settings.bank_card = command.bank_card.strip()
            settings.confirmation_phone_number = command.confirmation_phone_number.strip()
            await self.uow.commit()
            return PlatformPaymentSettingsDTO(
                settings.bank_card, settings.confirmation_phone_number
            )


class CreateExchangeRateHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: CreateExchangeRate) -> ExchangeRateDTO:
        if command.value_in_cup <= 0:
            raise ValidationError("Exchange rate value must be positive")
        async with self.uow:
            await require_platform_admin(self.uow.session, command.actor_user_id)
            currency = command.currency.upper()
            existing = await self.uow.session.scalar(
                select(ExchangeRateModel.id).where(ExchangeRateModel.currency == currency)
            )
            if existing:
                raise ConflictError("An exchange rate already exists for this currency")
            rate = ExchangeRateModel(currency=currency, value_in_cup=command.value_in_cup)
            self.uow.session.add(rate)
            await self.uow.commit()
            return ExchangeRateDTO(rate.id, rate.currency, rate.value_in_cup)


class UpdateExchangeRateHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: UpdateExchangeRate) -> ExchangeRateDTO:
        if command.value_in_cup <= 0:
            raise ValidationError("Exchange rate value must be positive")
        async with self.uow:
            await require_platform_admin(self.uow.session, command.actor_user_id)
            rate = await self.uow.session.get(ExchangeRateModel, command.rate_id)
            if rate is None:
                raise NotFoundError("Exchange rate not found")
            currency = command.currency.upper()
            duplicate = await self.uow.session.scalar(
                select(ExchangeRateModel.id).where(
                    ExchangeRateModel.currency == currency,
                    ExchangeRateModel.id != rate.id,
                )
            )
            if duplicate:
                raise ConflictError("An exchange rate already exists for this currency")
            rate.currency = currency
            rate.value_in_cup = command.value_in_cup
            await self.uow.commit()
            return ExchangeRateDTO(rate.id, rate.currency, rate.value_in_cup)


class DeleteExchangeRateHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: DeleteExchangeRate) -> None:
        async with self.uow:
            await require_platform_admin(self.uow.session, command.actor_user_id)
            rate = await self.uow.session.get(ExchangeRateModel, command.rate_id)
            if rate is None:
                raise NotFoundError("Exchange rate not found")
            await self.uow.session.delete(rate)
            await self.uow.commit()


class CreateSubscriptionPaymentHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: CreateSubscriptionPayment) -> SubscriptionPaymentDTO:
        _validate_payment_dates_and_amount(
            command.execution_date, command.expiration_date, command.amount_paid
        )
        async with self.uow:
            await require_platform_admin(self.uow.session, command.actor_user_id)
            if await self.uow.session.get(BusinessModel, command.business_id) is None:
                raise NotFoundError("Business not found")
            duplicate = await self.uow.session.scalar(
                select(SubscriptionPaymentModel.id).where(
                    SubscriptionPaymentModel.transaction_number
                    == command.transaction_number.strip()
                )
            )
            if duplicate:
                raise ConflictError("This transaction number is already registered")
            payment = SubscriptionPaymentModel(
                business_id=command.business_id,
                transaction_number=command.transaction_number.strip(),
                plan=command.plan,
                phone_number=command.phone_number.strip(),
                execution_date=command.execution_date,
                expiration_date=command.expiration_date,
                amount_paid=command.amount_paid,
            )
            self.uow.session.add(payment)
            await self.uow.commit()
            return _payment_dto(payment)


class UpdateSubscriptionPaymentHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: UpdateSubscriptionPayment) -> SubscriptionPaymentDTO:
        _validate_payment_dates_and_amount(
            command.execution_date, command.expiration_date, command.amount_paid
        )
        async with self.uow:
            await require_platform_admin(self.uow.session, command.actor_user_id)
            payment = await self.uow.session.get(SubscriptionPaymentModel, command.payment_id)
            if payment is None:
                raise NotFoundError("Subscription payment not found")
            transaction_number = command.transaction_number.strip()
            duplicate = await self.uow.session.scalar(
                select(SubscriptionPaymentModel.id).where(
                    SubscriptionPaymentModel.transaction_number == transaction_number,
                    SubscriptionPaymentModel.id != payment.id,
                )
            )
            if duplicate:
                raise ConflictError("This transaction number is already registered")
            payment.transaction_number = transaction_number
            payment.plan = command.plan
            payment.phone_number = command.phone_number.strip()
            payment.execution_date = command.execution_date
            payment.expiration_date = command.expiration_date
            payment.amount_paid = command.amount_paid
            await self.uow.commit()
            return _payment_dto(payment)


class DeleteSubscriptionPaymentHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: DeleteSubscriptionPayment) -> None:
        async with self.uow:
            await require_platform_admin(self.uow.session, command.actor_user_id)
            payment = await self.uow.session.get(SubscriptionPaymentModel, command.payment_id)
            if payment is None:
                raise NotFoundError("Subscription payment not found")
            await self.uow.session.delete(payment)
            await self.uow.commit()
