import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.orders.infrastructure.models.order import OrderModel


class SqlAlchemyOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_idempotency_key(self, business_id: uuid.UUID, key: str) -> OrderModel | None:
        return await self.session.scalar(
            select(OrderModel).where(
                OrderModel.business_id == business_id, OrderModel.idempotency_key == key
            )
        )

    async def add(self, order: OrderModel) -> None:
        self.session.add(order)
        await self.session.flush()
