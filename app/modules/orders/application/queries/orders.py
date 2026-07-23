import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.modules.orders.application.dto.orders import OrderDetailDTO, OrderDTO, OrderItemDTO
from app.modules.orders.infrastructure.models.order import OrderItemModel, OrderModel
from app.shared.domain.exceptions import NotFoundError


@dataclass(frozen=True)
class ListOrders:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    status: str | None = None


@dataclass(frozen=True)
class GetOrder:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    order_id: uuid.UUID


async def _require_member(
    session: AsyncSession, business_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    await BusinessAuthorizationService(session).require(
        user_id, business_id, BusinessPermission.MANAGE_ORDERS
    )


class ListOrdersHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: ListOrders) -> list[OrderDTO]:
        await _require_member(self.session, query.business_id, query.actor_user_id)
        statement = select(OrderModel).where(OrderModel.business_id == query.business_id)
        if query.status:
            statement = statement.where(OrderModel.status == query.status)
        orders = await self.session.scalars(statement.order_by(OrderModel.created_at.desc()))
        return [
            OrderDTO(x.id, x.order_number, x.status, x.currency, x.subtotal, x.total)
            for x in orders
        ]


class GetOrderHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: GetOrder) -> OrderDetailDTO:
        await _require_member(self.session, query.business_id, query.actor_user_id)
        order = await self.session.scalar(
            select(OrderModel).where(
                OrderModel.id == query.order_id, OrderModel.business_id == query.business_id
            )
        )
        if order is None:
            raise NotFoundError("Order not found")
        items = await self.session.scalars(
            select(OrderItemModel).where(OrderItemModel.order_id == order.id)
        )
        return OrderDetailDTO(
            order.id,
            order.order_number,
            order.status,
            order.currency,
            order.subtotal,
            order.total,
            order.customer_name,
            order.customer_email,
            order.customer_phone,
            order.notes,
            [
                OrderItemDTO(
                    x.id, x.product_id, x.product_name, x.unit_price, x.quantity, x.line_total
                )
                for x in items
            ],
        )
