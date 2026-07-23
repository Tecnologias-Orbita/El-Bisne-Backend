import uuid
from typing import Protocol

from app.modules.businesses.infrastructure.models.business import BusinessModel


class BusinessRepository(Protocol):
    async def get_by_slug(self, slug: str) -> BusinessModel | None: ...

    async def add(self, business: BusinessModel) -> None: ...

    async def user_can_manage(self, business_id: uuid.UUID, user_id: uuid.UUID) -> bool: ...
