import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.modules.businesses.infrastructure.repositories.sqlalchemy_businesses import (
    SqlAlchemyBusinessRepository,
)
from app.modules.services.application.commands.services import service_dto
from app.modules.services.application.dto.services import ServiceDTO
from app.modules.services.infrastructure.repositories.sqlalchemy_services import (
    SqlAlchemyServiceRepository,
)
from app.shared.domain.exceptions import NotFoundError


@dataclass(frozen=True)
class ListServices:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID


@dataclass(frozen=True)
class GetService:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    service_id: uuid.UUID


@dataclass(frozen=True)
class ListPublicServices:
    business_slug: str


class ListServicesHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: ListServices) -> list[ServiceDTO]:
        await BusinessAuthorizationService(self.session).require(
            query.actor_user_id, query.business_id, BusinessPermission.VIEW
        )
        return [
            service_dto(item)
            for item in await SqlAlchemyServiceRepository(self.session).list(query.business_id)
        ]


class GetServiceHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: GetService) -> ServiceDTO:
        await BusinessAuthorizationService(self.session).require(
            query.actor_user_id, query.business_id, BusinessPermission.VIEW
        )
        item = await SqlAlchemyServiceRepository(self.session).get(
            query.business_id, query.service_id
        )
        if item is None or item.archived_at is not None:
            raise NotFoundError("Service not found")
        return service_dto(item)


class ListPublicServicesHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: ListPublicServices) -> list[ServiceDTO]:
        business = await SqlAlchemyBusinessRepository(self.session).get_by_slug(query.business_slug)
        if business is None or not business.is_published or business.archived_at is not None:
            raise NotFoundError("Business not found")
        return [
            service_dto(item)
            for item in await SqlAlchemyServiceRepository(self.session).list_public(business.id)
        ]
