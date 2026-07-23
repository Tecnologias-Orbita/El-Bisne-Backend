from dataclasses import dataclass
from datetime import UTC, datetime

from app.modules.auth.application.dto.auth import TokenPairDTO, UserDTO
from app.modules.auth.infrastructure.models.user import RefreshTokenModel, UserModel
from app.modules.auth.infrastructure.repositories.sqlalchemy_users import SqlAlchemyUserRepository
from app.shared.application.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.domain.exceptions import ConflictError, UnauthorizedError
from app.shared.infrastructure.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


@dataclass(frozen=True)
class RegisterUser:
    email: str
    password: str
    full_name: str


@dataclass(frozen=True)
class LoginUser:
    email: str
    password: str


@dataclass(frozen=True)
class RefreshSession:
    refresh_token: str


class RegisterUserHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: RegisterUser) -> UserDTO:
        async with self.uow:
            users = SqlAlchemyUserRepository(self.uow.session)
            if await users.get_by_email(command.email):
                raise ConflictError("An account with this email already exists")
            user = UserModel(
                email=command.email.lower(),
                password_hash=hash_password(command.password),
                full_name=command.full_name.strip(),
            )
            await users.add(user)
            await self.uow.commit()
            return UserDTO(user.id, user.email, user.full_name, user.is_platform_admin)


class LoginUserHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: LoginUser) -> TokenPairDTO:
        async with self.uow:
            users = SqlAlchemyUserRepository(self.uow.session)
            user = await users.get_by_email(command.email)
            if (
                user is None
                or not user.is_active
                or not verify_password(command.password, user.password_hash)
            ):
                raise UnauthorizedError("Invalid email or password")
            raw, token_hash, expires_at = create_refresh_token()
            await users.add_refresh_token(
                RefreshTokenModel(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
            )
            await self.uow.commit()
            return TokenPairDTO(create_access_token(str(user.id)), raw)


class RefreshSessionHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: RefreshSession) -> TokenPairDTO:
        async with self.uow:
            users = SqlAlchemyUserRepository(self.uow.session)
            stored = await users.get_refresh_token(hash_refresh_token(command.refresh_token))
            if (
                stored is None
                or stored.revoked_at is not None
                or stored.expires_at <= datetime.now(UTC)
            ):
                raise UnauthorizedError("Invalid or expired refresh token")
            stored.revoked_at = datetime.now(UTC)
            raw, token_hash, expires_at = create_refresh_token()
            await users.add_refresh_token(
                RefreshTokenModel(
                    user_id=stored.user_id, token_hash=token_hash, expires_at=expires_at
                )
            )
            await self.uow.commit()
            return TokenPairDTO(create_access_token(str(stored.user_id)), raw)
