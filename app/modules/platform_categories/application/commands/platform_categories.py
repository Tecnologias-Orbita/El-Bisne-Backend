import uuid
from dataclasses import dataclass

from sqlalchemy import or_, select

from app.modules.billing.application.services import require_platform_admin
from app.modules.businesses.application.services.slugs import normalize_slug
from app.modules.platform_categories.application.dto.platform_category import (
    PlatformCategoryDTO,
)
from app.modules.platform_categories.infrastructure.models.platform_category import (
    PlatformCategoryModel,
)
from app.shared.application.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.domain.exceptions import ConflictError, NotFoundError


@dataclass(frozen=True)
class CreatePlatformCategory:
    actor_user_id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    is_active: bool = True


@dataclass(frozen=True)
class UpdatePlatformCategory:
    actor_user_id: uuid.UUID
    category_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    is_active: bool


@dataclass(frozen=True)
class DeletePlatformCategory:
    actor_user_id: uuid.UUID
    category_id: uuid.UUID


def _dto(category: PlatformCategoryModel) -> PlatformCategoryDTO:
    return PlatformCategoryDTO(
        category.id, category.name, category.slug, category.description, category.is_active
    )


async def _ensure_unique(uow: SqlAlchemyUnitOfWork, name: str, slug: str, exclude=None):
    statement = select(PlatformCategoryModel.id).where(
        or_(PlatformCategoryModel.name.ilike(name), PlatformCategoryModel.slug == slug)
    )
    if exclude is not None:
        statement = statement.where(PlatformCategoryModel.id != exclude)
    if await uow.session.scalar(statement):
        raise ConflictError("Platform category name or slug already exists")


class CreatePlatformCategoryHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: CreatePlatformCategory) -> PlatformCategoryDTO:
        async with self.uow:
            await require_platform_admin(self.uow.session, command.actor_user_id)
            name = command.name.strip()
            slug = normalize_slug(command.slug)
            await _ensure_unique(self.uow, name, slug)
            category = PlatformCategoryModel(
                name=name, slug=slug, description=command.description, is_active=command.is_active
            )
            self.uow.session.add(category)
            await self.uow.commit()
            return _dto(category)


class UpdatePlatformCategoryHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: UpdatePlatformCategory) -> PlatformCategoryDTO:
        async with self.uow:
            await require_platform_admin(self.uow.session, command.actor_user_id)
            category = await self.uow.session.get(PlatformCategoryModel, command.category_id)
            if category is None:
                raise NotFoundError("Platform category not found")
            name = command.name.strip()
            slug = normalize_slug(command.slug)
            await _ensure_unique(self.uow, name, slug, category.id)
            category.name = name
            category.slug = slug
            category.description = command.description
            category.is_active = command.is_active
            await self.uow.commit()
            return _dto(category)


class DeletePlatformCategoryHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: DeletePlatformCategory) -> None:
        async with self.uow:
            await require_platform_admin(self.uow.session, command.actor_user_id)
            category = await self.uow.session.get(PlatformCategoryModel, command.category_id)
            if category is None:
                raise NotFoundError("Platform category not found")
            await self.uow.session.delete(category)
            await self.uow.commit()
