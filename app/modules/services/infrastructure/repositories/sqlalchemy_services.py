from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.services.infrastructure.models.service import ServiceModel


class SqlAlchemyServiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, service: ServiceModel) -> None:
        self.session.add(service)
        await self.session.flush()

    async def get(self, business_id: uuid.UUID, service_id: uuid.UUID) -> ServiceModel | None:
        return await self.session.scalar(
            select(ServiceModel).where(
                ServiceModel.id == service_id, ServiceModel.business_id == business_id
            )
        )

    async def slug_exists(
        self, business_id: uuid.UUID, slug: str, excluding_id: uuid.UUID | None = None
    ) -> bool:
        statement = select(ServiceModel.id).where(
            ServiceModel.business_id == business_id, ServiceModel.slug == slug
        )
        if excluding_id:
            statement = statement.where(ServiceModel.id != excluding_id)
        return await self.session.scalar(statement) is not None

    async def list(self, business_id: uuid.UUID) -> list[ServiceModel]:
        return list(
            await self.session.scalars(
                select(ServiceModel)
                .where(ServiceModel.business_id == business_id, ServiceModel.archived_at.is_(None))
                .order_by(ServiceModel.name)
            )
        )

    async def list_public(self, business_id: uuid.UUID) -> list[ServiceModel]:
        return list(
            await self.session.scalars(
                select(ServiceModel)
                .where(
                    ServiceModel.business_id == business_id,
                    ServiceModel.is_published.is_(True),
                    ServiceModel.is_available.is_(True),
                    ServiceModel.archived_at.is_(None),
                )
                .order_by(ServiceModel.name)
            )
        )
