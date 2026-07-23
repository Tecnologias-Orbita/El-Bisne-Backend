import uuid
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.infrastructure.models.user import UserModel
from app.modules.businesses.infrastructure.models.business import BusinessMemberModel
from app.shared.domain.exceptions import ForbiddenError, UnauthorizedError


class BusinessPermission(StrEnum):
    VIEW = "view"
    MANAGE_BUSINESS = "manage_business"
    MANAGE_MEMBERS = "manage_members"
    MANAGE_CONTENT = "manage_content"
    MANAGE_ORDERS = "manage_orders"
    VIEW_ANALYTICS = "view_analytics"


ROLE_PERMISSIONS: dict[str, set[BusinessPermission]] = {
    "owner": set(BusinessPermission),
    "admin": set(BusinessPermission),
    "editor": {BusinessPermission.VIEW, BusinessPermission.MANAGE_CONTENT},
    "viewer": {BusinessPermission.VIEW, BusinessPermission.VIEW_ANALYTICS},
}


class BusinessAuthorizationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def is_platform_admin(self, user_id: uuid.UUID) -> bool:
        value = await self.session.scalar(
            select(UserModel.is_platform_admin).where(
                UserModel.id == user_id,
                UserModel.is_active.is_(True),
                UserModel.archived_at.is_(None),
            )
        )
        return bool(value)

    async def get_role(self, user_id: uuid.UUID, business_id: uuid.UUID) -> str | None:
        return await self.session.scalar(
            select(BusinessMemberModel.role).where(
                BusinessMemberModel.user_id == user_id,
                BusinessMemberModel.business_id == business_id,
            )
        )

    async def require(
        self,
        user_id: uuid.UUID,
        business_id: uuid.UUID,
        permission: BusinessPermission,
    ) -> str:
        user_exists = await self.session.scalar(
            select(UserModel.id).where(
                UserModel.id == user_id,
                UserModel.is_active.is_(True),
                UserModel.archived_at.is_(None),
            )
        )
        if user_exists is None:
            raise UnauthorizedError("User is unavailable")
        if await self.is_platform_admin(user_id):
            return "platform_admin"
        role = await self.get_role(user_id, business_id)
        if role is None or permission not in ROLE_PERMISSIONS.get(role, set()):
            raise ForbiddenError("You do not have permission for this business operation")
        return role
