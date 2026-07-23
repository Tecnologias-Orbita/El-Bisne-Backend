import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, EmailStr, Field

from app.modules.auth.api.routes import get_current_user
from app.modules.auth.application.dto.auth import UserDTO
from app.modules.orders.application.commands.orders import ChangeOrderStatus, CreateGuestOrder
from app.modules.orders.application.dto.orders import OrderDetailDTO, OrderDTO, OrderItemInput
from app.modules.orders.application.queries.orders import GetOrder, ListOrders
from app.shared.application.cqrs import CommandBus, QueryBus
from app.shared.infrastructure.dependencies import get_command_bus, get_query_bus

router = APIRouter(prefix="/public/businesses", tags=["public-orders"])
admin_router = APIRouter(prefix="/businesses/{business_id}/orders", tags=["orders"])


class OrderItemRequest(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(ge=1, le=999)


class CreateOrderRequest(BaseModel):
    customer_name: str = Field(min_length=2, max_length=160)
    customer_email: EmailStr | None = None
    customer_phone: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=2000)
    items: list[OrderItemRequest] = Field(min_length=1, max_length=100)


class OrderStatusRequest(BaseModel):
    status: str
    comment: str | None = Field(default=None, max_length=1000)


@router.post(
    "/{business_slug}/orders",
    response_model=OrderDTO,
    status_code=status.HTTP_201_CREATED,
)
async def create_guest_order(
    business_slug: str,
    body: CreateOrderRequest,
    bus: Annotated[CommandBus, Depends(get_command_bus)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)],
) -> OrderDTO:
    return await bus.dispatch(
        CreateGuestOrder(
            business_slug=business_slug,
            idempotency_key=idempotency_key,
            customer_name=body.customer_name,
            customer_email=str(body.customer_email) if body.customer_email else None,
            customer_phone=body.customer_phone,
            notes=body.notes,
            items=[OrderItemInput(**item.model_dump()) for item in body.items],
        )
    )


@admin_router.get("", response_model=list[OrderDTO])
async def list_orders(
    business_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
    order_status: str | None = None,
) -> list[OrderDTO]:
    return await bus.dispatch(ListOrders(user.id, business_id, order_status))


@admin_router.get("/{order_id}", response_model=OrderDetailDTO)
async def get_order(
    business_id: uuid.UUID,
    order_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> OrderDetailDTO:
    return await bus.dispatch(GetOrder(user.id, business_id, order_id))


@admin_router.patch("/{order_id}/status", response_model=OrderDTO)
async def change_order_status(
    business_id: uuid.UUID,
    order_id: uuid.UUID,
    body: OrderStatusRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> OrderDTO:
    return await bus.dispatch(
        ChangeOrderStatus(user.id, business_id, order_id, body.status, body.comment)
    )
