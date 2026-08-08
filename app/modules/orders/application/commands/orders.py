import uuid
from dataclasses import dataclass

from sqlalchemy import select

from app.modules.analytics.infrastructure.models.analytics import AnalyticsEventModel
from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.modules.businesses.infrastructure.repositories.sqlalchemy_businesses import (
    SqlAlchemyBusinessRepository,
)
from app.modules.catalog.infrastructure.repositories.sqlalchemy_catalog import (
    SqlAlchemyCatalogRepository,
)
from app.modules.notifications.infrastructure.models.notification import OutboxEventModel
from app.modules.orders.application.dto.orders import OrderDTO, OrderItemInput
from app.modules.orders.application.services.order_pricing import calculate_order
from app.modules.orders.infrastructure.models.order import (
    OrderItemModel,
    OrderModel,
    OrderStatusHistoryModel,
)
from app.modules.orders.infrastructure.repositories.sqlalchemy_orders import (
    SqlAlchemyOrderRepository,
)
from app.shared.application.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.domain.exceptions import NotFoundError, ValidationError


@dataclass(frozen=True)
class CreateGuestOrder:
    business_slug: str
    idempotency_key: str
    customer_name: str
    customer_email: str | None
    customer_phone: str | None
    notes: str | None
    items: list[OrderItemInput]


class CreateGuestOrderHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: CreateGuestOrder) -> OrderDTO:
        if not command.customer_email and not command.customer_phone:
            raise ValidationError("An email or phone number is required")
        async with self.uow:
            business = await SqlAlchemyBusinessRepository(self.uow.session).get_by_slug(
                command.business_slug
            )
            if business is None or not business.is_published or business.archived_at is not None:
                raise NotFoundError("Business not found")
            if not business.sells_online:
                raise ValidationError("This business does not accept online orders")
            orders = SqlAlchemyOrderRepository(self.uow.session)
            existing = await orders.get_by_idempotency_key(business.id, command.idempotency_key)
            if existing is not None:
                return OrderDTO(
                    existing.id,
                    existing.order_number,
                    existing.status,
                    existing.currency,
                    existing.subtotal,
                    existing.total,
                )
            product_ids = list({item.product_id for item in command.items})
            products = await SqlAlchemyCatalogRepository(self.uow.session).get_available_products(
                business.id, product_ids
            )
            lines, total = calculate_order(command.items, products)
            order = OrderModel(
                business_id=business.id,
                order_number=f"ORD-{uuid.uuid4().hex[:10].upper()}",
                idempotency_key=command.idempotency_key,
                customer_name=command.customer_name.strip(),
                customer_email=command.customer_email,
                customer_phone=command.customer_phone,
                notes=command.notes,
                currency=business.currency,
                subtotal=total,
                total=total,
            )
            await orders.add(order)
            for product, quantity, line_total in lines:
                self.uow.session.add(
                    OrderItemModel(
                        order_id=order.id,
                        product_id=product.id,
                        product_name=product.name,
                        unit_price=product.price,
                        quantity=quantity,
                        line_total=line_total,
                    )
                )
            self.uow.session.add(OrderStatusHistoryModel(order_id=order.id, to_status="pending"))
            self.uow.session.add(
                OutboxEventModel(
                    event_type="order.created",
                    payload={
                        "order_id": str(order.id),
                        "business_id": str(business.id),
                        "recipient": business.contact_email,
                    },
                )
            )
            self.uow.session.add(
                AnalyticsEventModel(
                    business_id=business.id,
                    event_type="order_created",
                    resource_type="order",
                    resource_id=order.id,
                )
            )
            await self.uow.commit()
            return OrderDTO(
                order.id,
                order.order_number,
                order.status,
                order.currency,
                order.subtotal,
                order.total,
            )


@dataclass(frozen=True)
class ChangeOrderStatus:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    order_id: uuid.UUID
    status: str
    comment: str | None = None


ALLOWED_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


class ChangeOrderStatusHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: ChangeOrderStatus) -> OrderDTO:
        async with self.uow:
            await BusinessAuthorizationService(self.uow.session).require(
                command.actor_user_id, command.business_id, BusinessPermission.MANAGE_ORDERS
            )
            order = await self.uow.session.scalar(
                select(OrderModel).where(
                    OrderModel.id == command.order_id,
                    OrderModel.business_id == command.business_id,
                )
            )
            if order is None:
                raise NotFoundError("Order not found")
            if command.status not in ALLOWED_TRANSITIONS.get(order.status, set()):
                raise ValidationError(
                    f"Order cannot transition from {order.status} to {command.status}"
                )
            previous = order.status
            order.status = command.status
            self.uow.session.add(
                OrderStatusHistoryModel(
                    order_id=order.id,
                    actor_user_id=command.actor_user_id,
                    from_status=previous,
                    to_status=command.status,
                    comment=command.comment,
                )
            )
            await self.uow.commit()
            return OrderDTO(
                order.id,
                order.order_number,
                order.status,
                order.currency,
                order.subtotal,
                order.total,
            )
