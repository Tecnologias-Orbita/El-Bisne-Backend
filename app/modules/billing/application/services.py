import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.infrastructure.models.user import UserModel
from app.shared.domain.exceptions import ForbiddenError


async def require_platform_admin(session: AsyncSession, user_id: uuid.UUID) -> None:
    is_admin = await session.scalar(
        select(UserModel.is_platform_admin).where(
            UserModel.id == user_id,
            UserModel.is_active.is_(True),
            UserModel.archived_at.is_(None),
        )
    )
    if not is_admin:
        raise ForbiddenError("Platform administrator access is required")
