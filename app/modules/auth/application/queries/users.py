import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.application.dto.auth import UserDTO
from app.modules.auth.infrastructure.models.user import UserModel
from app.modules.auth.infrastructure.repositories.sqlalchemy_users import SqlAlchemyUserRepository
from app.modules.billing.infrastructure.models.billing import SubscriptionPaymentModel
from app.modules.businesses.application.services.slugs import normalize_slug
from app.modules.businesses.infrastructure.models.business import BusinessModel
from app.shared.domain.exceptions import UnauthorizedError


@dataclass(frozen=True)
class GetCurrentUser:
    user_id: uuid.UUID


@dataclass(frozen=True)
class CheckOnboardingAvailability:
    email: str | None = None
    slug: str | None = None
    transaction_number: str | None = None


@dataclass(frozen=True)
class OnboardingAvailabilityDTO:
    email_available: bool | None
    slug_available: bool | None
    transaction_available: bool | None


class CheckOnboardingAvailabilityHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: CheckOnboardingAvailability) -> OnboardingAvailabilityDTO:
        email_available = None
        slug_available = None
        transaction_available = None
        if query.email:
            existing = await self.session.scalar(
                select(UserModel.id).where(UserModel.email == query.email.strip().lower())
            )
            email_available = existing is None
        if query.slug:
            existing = await self.session.scalar(
                select(BusinessModel.id).where(BusinessModel.slug == normalize_slug(query.slug))
            )
            slug_available = existing is None
        if query.transaction_number:
            existing = await self.session.scalar(
                select(SubscriptionPaymentModel.id).where(
                    SubscriptionPaymentModel.transaction_number == query.transaction_number.strip()
                )
            )
            transaction_available = existing is None
        return OnboardingAvailabilityDTO(email_available, slug_available, transaction_available)


class GetCurrentUserHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: GetCurrentUser) -> UserDTO:
        user = await SqlAlchemyUserRepository(self.session).get_by_id(query.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("User is unavailable")
        return UserDTO(user.id, user.email, user.full_name, user.is_platform_admin)
