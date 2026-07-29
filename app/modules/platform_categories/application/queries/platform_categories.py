import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.application.services import require_platform_admin
from app.modules.platform_categories.application.dto.platform_category import PlatformCategoryDTO
from app.modules.platform_categories.infrastructure.models.platform_category import (
    PlatformCategoryModel,
)


@dataclass(frozen=True)
class ListPlatformCategories:
    actor_user_id: uuid.UUID
    include_inactive: bool = False


class ListPlatformCategoriesHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: ListPlatformCategories) -> list[PlatformCategoryDTO]:
        if query.include_inactive:
            await require_platform_admin(self.session, query.actor_user_id)
        statement = select(PlatformCategoryModel)
        if not query.include_inactive:
            statement = statement.where(PlatformCategoryModel.is_active.is_(True))
        categories = await self.session.scalars(statement.order_by(PlatformCategoryModel.name))
        return [
            PlatformCategoryDTO(x.id, x.name, x.slug, x.description, x.is_active)
            for x in categories
        ]
