import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.businesses.infrastructure.models.business import (
    BusinessMemberModel,
    BusinessModel,
)


class SqlAlchemyBusinessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_slug(self, slug: str) -> BusinessModel | None:
        return await self.session.scalar(select(BusinessModel).where(BusinessModel.slug == slug))

    async def add(self, business: BusinessModel) -> None:
        self.session.add(business)
        await self.session.flush()

    async def add_member(self, member: BusinessMemberModel) -> None:
        self.session.add(member)
        await self.session.flush()

    async def user_can_manage(self, business_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        membership = await self.session.scalar(
            select(BusinessMemberModel.id).where(
                BusinessMemberModel.business_id == business_id,
                BusinessMemberModel.user_id == user_id,
                BusinessMemberModel.role.in_(("owner", "admin", "editor")),
            )
        )
        return membership is not None

    async def get_member(
        self, business_id: uuid.UUID, user_id: uuid.UUID
    ) -> BusinessMemberModel | None:
        return await self.session.scalar(
            select(BusinessMemberModel).where(
                BusinessMemberModel.business_id == business_id,
                BusinessMemberModel.user_id == user_id,
            )
        )

    async def get_by_id(self, business_id: uuid.UUID) -> BusinessModel | None:
        return await self.session.get(BusinessModel, business_id)

    async def list_for_user(self, user_id: uuid.UUID) -> list[BusinessModel]:
        result = await self.session.scalars(
            select(BusinessModel)
            .join(BusinessMemberModel)
            .where(BusinessMemberModel.user_id == user_id, BusinessModel.archived_at.is_(None))
            .order_by(BusinessModel.name)
        )
        return list(result)
