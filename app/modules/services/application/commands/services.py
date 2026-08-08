import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.modules.businesses.application.services.slugs import normalize_slug
from app.modules.catalog.infrastructure.repositories.sqlalchemy_catalog import (
    SqlAlchemyCatalogRepository,
)
from app.modules.platform_categories.infrastructure.models.platform_category import (
    PlatformCategoryModel,
)
from app.modules.services.application.dto.services import ServiceDTO
from app.modules.services.infrastructure.models.service import ServiceModel
from app.modules.services.infrastructure.repositories.sqlalchemy_services import (
    SqlAlchemyServiceRepository,
)
from app.shared.application.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.domain.exceptions import ConflictError, NotFoundError, ValidationError


@dataclass(frozen=True, kw_only=True)
class CreateService:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    name: str
    slug: str
    category_id: uuid.UUID | None = None
    platform_category_id: uuid.UUID | None = None
    description: str | None = None
    price: Decimal | None = None
    currency: str | None = None
    duration_minutes: int | None = None
    image_url: str | None = None
    is_available: bool = True
    is_published: bool = False


@dataclass(frozen=True, kw_only=True)
class UpdateService(CreateService):
    service_id: uuid.UUID


@dataclass(frozen=True)
class ArchiveService:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    service_id: uuid.UUID


def service_dto(service: ServiceModel) -> ServiceDTO:
    return ServiceDTO(
        service.id,
        service.category_id,
        service.platform_category_id,
        service.name,
        service.slug,
        service.description,
        service.price,
        service.currency,
        service.duration_minutes,
        service.image_url,
        service.is_available,
        service.is_published,
    )


async def _validate(uow: SqlAlchemyUnitOfWork, command: CreateService) -> None:
    if command.price is not None and command.price < 0:
        raise ValidationError("Price cannot be negative")
    if command.duration_minutes is not None and command.duration_minutes < 1:
        raise ValidationError("Duration must be at least one minute")
    if (command.price is None) != (command.currency is None):
        raise ValidationError("Price and currency must be provided together")
    if command.category_id and not await SqlAlchemyCatalogRepository(uow.session).get_category(
        command.business_id, command.category_id
    ):
        raise ValidationError("Category does not belong to this business")
    if command.platform_category_id:
        category = await uow.session.get(PlatformCategoryModel, command.platform_category_id)
        if category is None or not category.is_active:
            raise ValidationError("Platform category does not exist or is inactive")


class CreateServiceHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: CreateService) -> ServiceDTO:
        async with self.uow:
            await BusinessAuthorizationService(self.uow.session).require(
                command.actor_user_id, command.business_id, BusinessPermission.MANAGE_CONTENT
            )
            await _validate(self.uow, command)
            repo = SqlAlchemyServiceRepository(self.uow.session)
            slug = normalize_slug(command.slug)
            if await repo.slug_exists(command.business_id, slug):
                raise ConflictError("Service slug already exists")
            service = ServiceModel(
                business_id=command.business_id,
                category_id=command.category_id,
                platform_category_id=command.platform_category_id,
                name=command.name.strip(),
                slug=slug,
                description=command.description,
                price=command.price,
                currency=command.currency.upper() if command.currency else None,
                duration_minutes=command.duration_minutes,
                image_url=command.image_url,
                is_available=command.is_available,
                is_published=command.is_published,
            )
            await repo.add(service)
            await self.uow.commit()
            return service_dto(service)


class UpdateServiceHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: UpdateService) -> ServiceDTO:
        async with self.uow:
            await BusinessAuthorizationService(self.uow.session).require(
                command.actor_user_id, command.business_id, BusinessPermission.MANAGE_CONTENT
            )
            await _validate(self.uow, command)
            repo = SqlAlchemyServiceRepository(self.uow.session)
            service = await repo.get(command.business_id, command.service_id)
            if service is None or service.archived_at is not None:
                raise NotFoundError("Service not found")
            slug = normalize_slug(command.slug)
            if await repo.slug_exists(command.business_id, slug, service.id):
                raise ConflictError("Service slug already exists")
            for field in (
                "category_id",
                "platform_category_id",
                "description",
                "price",
                "duration_minutes",
                "image_url",
                "is_available",
                "is_published",
            ):
                setattr(service, field, getattr(command, field))
            service.name = command.name.strip()
            service.slug = slug
            service.currency = command.currency.upper() if command.currency else None
            await self.uow.commit()
            return service_dto(service)


class ArchiveServiceHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: ArchiveService) -> None:
        async with self.uow:
            await BusinessAuthorizationService(self.uow.session).require(
                command.actor_user_id, command.business_id, BusinessPermission.MANAGE_CONTENT
            )
            service = await SqlAlchemyServiceRepository(self.uow.session).get(
                command.business_id, command.service_id
            )
            if service is None:
                raise NotFoundError("Service not found")
            service.archived_at = datetime.now(UTC)
            service.is_published = False
            service.is_available = False
            await self.uow.commit()
