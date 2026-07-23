import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.infrastructure.models.user import RefreshTokenModel, UserModel


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> UserModel | None:
        return await self.session.scalar(select(UserModel).where(UserModel.email == email.lower()))

    async def get_by_id(self, user_id: uuid.UUID) -> UserModel | None:
        return await self.session.get(UserModel, user_id)

    async def add(self, user: UserModel) -> None:
        self.session.add(user)
        await self.session.flush()

    async def add_refresh_token(self, token: RefreshTokenModel) -> None:
        self.session.add(token)
        await self.session.flush()

    async def get_refresh_token(self, token_hash: str) -> RefreshTokenModel | None:
        return await self.session.scalar(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
