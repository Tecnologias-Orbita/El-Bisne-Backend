import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.application.dto.auth import UserDTO
from app.modules.auth.infrastructure.repositories.sqlalchemy_users import SqlAlchemyUserRepository
from app.shared.domain.exceptions import UnauthorizedError


@dataclass(frozen=True)
class GetCurrentUser:
    user_id: uuid.UUID


class GetCurrentUserHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: GetCurrentUser) -> UserDTO:
        user = await SqlAlchemyUserRepository(self.session).get_by_id(query.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("User is unavailable")
        return UserDTO(user.id, user.email, user.full_name, user.is_platform_admin)
