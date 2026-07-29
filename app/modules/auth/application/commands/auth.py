import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select

from app.modules.auth.application.dto.auth import BusinessOnboardingDTO, TokenPairDTO, UserDTO
from app.modules.auth.infrastructure.models.user import RefreshTokenModel, UserModel
from app.modules.auth.infrastructure.repositories.sqlalchemy_users import SqlAlchemyUserRepository
from app.modules.billing.domain.plans import SubscriptionPlan
from app.modules.billing.infrastructure.models.billing import SubscriptionPaymentModel
from app.modules.businesses.application.dto.business import BusinessDTO, BusinessSiteDTO
from app.modules.businesses.application.services.slugs import normalize_slug
from app.modules.businesses.infrastructure.models.business import (
    BusinessMemberModel,
    BusinessModel,
)
from app.modules.platform_categories.infrastructure.models.platform_category import (
    PlatformCategoryModel,
)
from app.modules.sites.infrastructure.models.site import BusinessSiteModel
from app.shared.application.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.domain.exceptions import ConflictError, UnauthorizedError, ValidationError
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


@dataclass(frozen=True)
class OnboardBusiness:
    email: str
    password: str
    full_name: str
    business_name: str
    slug: str
    business_type: str
    transaction_number: str
    plan: SubscriptionPlan
    phone_number: str
    execution_date: date
    expiration_date: date
    amount_paid: Decimal
    description: str | None = None
    currency: str = "USD"
    timezone: str = "America/Havana"
    contact_email: str | None = None
    contact_phone: str | None = None
    hero_image_url: str | None = None
    logo_url: str | None = None
    platform_category_id: uuid.UUID | None = None


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


class OnboardBusinessHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: OnboardBusiness) -> BusinessOnboardingDTO:
        if command.expiration_date < command.execution_date:
            raise ValidationError("Expiration date cannot be earlier than execution date")
        async with self.uow:
            if command.platform_category_id is not None:
                platform_category = await self.uow.session.get(
                    PlatformCategoryModel, command.platform_category_id
                )
                if platform_category is None or not platform_category.is_active:
                    raise ValidationError("Platform category does not exist or is inactive")
            users = SqlAlchemyUserRepository(self.uow.session)
            if await users.get_by_email(command.email):
                raise ConflictError("An account with this email already exists")
            slug = normalize_slug(command.slug)
            if await self.uow.session.scalar(
                select(BusinessModel.id).where(BusinessModel.slug == slug)
            ):
                raise ConflictError("This business slug is already in use")
            transaction_number = command.transaction_number.strip()
            if await self.uow.session.scalar(
                select(SubscriptionPaymentModel.id).where(
                    SubscriptionPaymentModel.transaction_number == transaction_number
                )
            ):
                raise ConflictError("This transaction number is already registered")

            user = UserModel(
                email=command.email.lower(),
                password_hash=hash_password(command.password),
                full_name=command.full_name.strip(),
            )
            await users.add(user)
            business = BusinessModel(
                name=command.business_name.strip(),
                slug=slug,
                business_type=command.business_type,
                description=command.description,
                currency=command.currency.upper(),
                timezone=command.timezone,
                contact_email=command.contact_email,
                contact_phone=command.contact_phone,
                platform_category_id=command.platform_category_id,
            )
            self.uow.session.add(business)
            await self.uow.session.flush()
            self.uow.session.add(
                BusinessMemberModel(business_id=business.id, user_id=user.id, role="owner")
            )
            site = BusinessSiteModel(
                business_id=business.id,
                hero_image_url=command.hero_image_url,
                logo_url=command.logo_url,
            )
            self.uow.session.add(site)
            self.uow.session.add(
                SubscriptionPaymentModel(
                    business_id=business.id,
                    transaction_number=transaction_number,
                    plan=command.plan,
                    phone_number=command.phone_number.strip(),
                    execution_date=command.execution_date,
                    expiration_date=command.expiration_date,
                    amount_paid=command.amount_paid,
                )
            )
            raw, token_hash, expires_at = create_refresh_token()
            await users.add_refresh_token(
                RefreshTokenModel(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
            )
            await self.uow.commit()
            return BusinessOnboardingDTO(
                UserDTO(user.id, user.email, user.full_name, user.is_platform_admin),
                BusinessDTO(
                    business.id,
                    business.name,
                    business.slug,
                    business.description,
                    business.business_type,
                    business.currency,
                    business.timezone,
                    business.contact_email,
                    business.contact_phone,
                    business.is_published,
                    business.platform_category_id,
                    BusinessSiteDTO(site.hero_image_url, site.logo_url),
                ),
                TokenPairDTO(create_access_token(str(user.id)), raw),
            )
