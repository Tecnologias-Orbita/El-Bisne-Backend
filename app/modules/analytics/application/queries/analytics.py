import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.application.dto.analytics import DashboardDTO
from app.modules.analytics.infrastructure.models.analytics import AnalyticsEventModel
from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.modules.orders.infrastructure.models.order import OrderModel


@dataclass(frozen=True)
class GetBusinessDashboard:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID


class GetBusinessDashboardHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: GetBusinessDashboard) -> DashboardDTO:
        await BusinessAuthorizationService(self.session).require(
            query.actor_user_id, query.business_id, BusinessPermission.VIEW_ANALYTICS
        )
        event_counts = dict(
            (
                await self.session.execute(
                    select(AnalyticsEventModel.event_type, func.count())
                    .where(AnalyticsEventModel.business_id == query.business_id)
                    .group_by(AnalyticsEventModel.event_type)
                )
            ).all()
        )
        order_counts = dict(
            (
                await self.session.execute(
                    select(OrderModel.status, func.count())
                    .where(OrderModel.business_id == query.business_id)
                    .group_by(OrderModel.status)
                )
            ).all()
        )
        visits = int(event_counts.get("site_view", 0))
        orders = sum(int(value) for value in order_counts.values())
        return DashboardDTO(
            visits=visits,
            product_views=int(event_counts.get("product_view", 0)),
            orders=orders,
            completed_orders=int(order_counts.get("completed", 0)),
            conversion_rate=round((orders / visits * 100) if visits else 0, 2),
        )
