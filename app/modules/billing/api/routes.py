import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field

from app.modules.auth.api.routes import get_current_user
from app.modules.auth.application.dto.auth import UserDTO
from app.modules.billing.application.commands.billing import (
    CreateExchangeRate,
    CreateSubscriptionPayment,
    DeleteExchangeRate,
    DeleteSubscriptionPayment,
    UpdateExchangeRate,
    UpdatePlatformPaymentSettings,
    UpdateSubscriptionPayment,
)
from app.modules.billing.application.dto.billing import (
    ExchangeRateDTO,
    PlatformPaymentSettingsDTO,
    SubscriptionPaymentDTO,
)
from app.modules.billing.application.queries.billing import (
    GetPlatformPaymentSettings,
    ListAllSubscriptionPayments,
    ListBusinessSubscriptionPayments,
    ListExchangeRates,
)
from app.modules.billing.domain.plans import SubscriptionPlan
from app.shared.application.cqrs import CommandBus, QueryBus
from app.shared.infrastructure.dependencies import get_command_bus, get_query_bus

public_router = APIRouter(prefix="/platform", tags=["platform"])
business_router = APIRouter(prefix="/businesses", tags=["subscription-payments"])
admin_router = APIRouter(prefix="/platform/admin", tags=["platform-admin"])


class PlatformPaymentSettingsRequest(BaseModel):
    bank_card: str = Field(min_length=4, max_length=32)
    confirmation_phone_number: str = Field(min_length=3, max_length=32)


class ExchangeRateRequest(BaseModel):
    currency: str = Field(min_length=3, max_length=3)
    value_in_cup: Decimal = Field(gt=0, max_digits=18, decimal_places=6)


class SubscriptionPaymentRequest(BaseModel):
    transaction_number: str = Field(min_length=1, max_length=120)
    plan: SubscriptionPlan
    phone_number: str = Field(min_length=3, max_length=32)
    execution_date: date
    expiration_date: date
    amount_paid: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class CreateSubscriptionPaymentRequest(SubscriptionPaymentRequest):
    business_id: uuid.UUID


@public_router.get("/payment-settings", response_model=PlatformPaymentSettingsDTO)
async def get_payment_settings(
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> PlatformPaymentSettingsDTO:
    return await bus.dispatch(GetPlatformPaymentSettings())


@public_router.get("/exchange-rates", response_model=list[ExchangeRateDTO])
async def list_exchange_rates(
    _user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> list[ExchangeRateDTO]:
    return await bus.dispatch(ListExchangeRates())


@business_router.get(
    "/{business_id}/subscription-payments", response_model=list[SubscriptionPaymentDTO]
)
async def list_business_payments(
    business_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
    payment_id: uuid.UUID | None = None,
    transaction_number: str | None = None,
    plan: SubscriptionPlan | None = None,
    phone_number: str | None = None,
    execution_date: date | None = None,
    expiration_date: date | None = None,
    amount_paid: Decimal | None = None,
    created_at: datetime | None = None,
) -> list[SubscriptionPaymentDTO]:
    return await bus.dispatch(
        ListBusinessSubscriptionPayments(
            actor_user_id=user.id,
            business_id=business_id,
            payment_id=payment_id,
            transaction_number=transaction_number,
            plan=plan,
            phone_number=phone_number,
            execution_date=execution_date,
            expiration_date=expiration_date,
            amount_paid=amount_paid,
            created_at=created_at,
        )
    )


@admin_router.put("/payment-settings", response_model=PlatformPaymentSettingsDTO)
async def update_payment_settings(
    body: PlatformPaymentSettingsRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> PlatformPaymentSettingsDTO:
    return await bus.dispatch(UpdatePlatformPaymentSettings(user.id, **body.model_dump()))


@admin_router.post(
    "/exchange-rates", response_model=ExchangeRateDTO, status_code=status.HTTP_201_CREATED
)
async def create_exchange_rate(
    body: ExchangeRateRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> ExchangeRateDTO:
    return await bus.dispatch(CreateExchangeRate(user.id, **body.model_dump()))


@admin_router.put("/exchange-rates/{rate_id}", response_model=ExchangeRateDTO)
async def update_exchange_rate(
    rate_id: uuid.UUID,
    body: ExchangeRateRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> ExchangeRateDTO:
    return await bus.dispatch(UpdateExchangeRate(user.id, rate_id, **body.model_dump()))


@admin_router.delete("/exchange-rates/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exchange_rate(
    rate_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> Response:
    await bus.dispatch(DeleteExchangeRate(user.id, rate_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.get("/subscription-payments", response_model=list[SubscriptionPaymentDTO])
async def list_all_payments(
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
    business_id: uuid.UUID | None = None,
    payment_id: uuid.UUID | None = None,
    business_name: str | None = None,
    transaction_number: str | None = None,
    plan: SubscriptionPlan | None = None,
    phone_number: str | None = None,
    execution_date: date | None = None,
    expiration_date: date | None = None,
    amount_paid: Decimal | None = None,
    created_at: datetime | None = None,
) -> list[SubscriptionPaymentDTO]:
    return await bus.dispatch(
        ListAllSubscriptionPayments(
            actor_user_id=user.id,
            business_id=business_id,
            payment_id=payment_id,
            business_name=business_name,
            transaction_number=transaction_number,
            plan=plan,
            phone_number=phone_number,
            execution_date=execution_date,
            expiration_date=expiration_date,
            amount_paid=amount_paid,
            created_at=created_at,
        )
    )


@admin_router.post(
    "/subscription-payments",
    response_model=SubscriptionPaymentDTO,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription_payment(
    body: CreateSubscriptionPaymentRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> SubscriptionPaymentDTO:
    return await bus.dispatch(CreateSubscriptionPayment(user.id, **body.model_dump()))


@admin_router.put("/subscription-payments/{payment_id}", response_model=SubscriptionPaymentDTO)
async def update_subscription_payment(
    payment_id: uuid.UUID,
    body: SubscriptionPaymentRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> SubscriptionPaymentDTO:
    return await bus.dispatch(UpdateSubscriptionPayment(user.id, payment_id, **body.model_dump()))


@admin_router.delete("/subscription-payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription_payment(
    payment_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> Response:
    await bus.dispatch(DeleteSubscriptionPayment(user.id, payment_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
