import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from app.modules.auth.infrastructure.repositories.sqlalchemy_users import SqlAlchemyUserRepository
from app.modules.businesses.application.dto.business import BusinessDTO
from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.modules.businesses.application.services.slugs import normalize_slug
from app.modules.businesses.infrastructure.models.business import (
    BusinessMemberModel,
    BusinessModel,
)
from app.modules.businesses.infrastructure.repositories.sqlalchemy_businesses import (
    SqlAlchemyBusinessRepository,
)
from app.modules.sites.infrastructure.models.site import BusinessSiteModel
from app.shared.application.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.domain.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


@dataclass(frozen=True)
class CreateBusiness:
    actor_user_id: uuid.UUID
    name: str
    slug: str
    business_type: str
    description: str | None = None
    currency: str = "USD"
    timezone: str = "America/Havana"
    contact_email: str | None = None
    contact_phone: str | None = None


class CreateBusinessHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: CreateBusiness) -> BusinessDTO:
        async with self.uow:
            repo = SqlAlchemyBusinessRepository(self.uow.session)
            slug = normalize_slug(command.slug)
            if await repo.get_by_slug(slug):
                raise ConflictError("This business slug is already in use")
            business = BusinessModel(
                name=command.name.strip(),
                slug=slug,
                business_type=command.business_type,
                description=command.description,
                currency=command.currency.upper(),
                timezone=command.timezone,
                contact_email=command.contact_email,
                contact_phone=command.contact_phone,
            )
            await repo.add(business)
            await repo.add_member(
                BusinessMemberModel(
                    business_id=business.id, user_id=command.actor_user_id, role="owner"
                )
            )
            self.uow.session.add(BusinessSiteModel(business_id=business.id))
            await self.uow.commit()
            return BusinessDTO(
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
            )


@dataclass(frozen=True)
class UpdateBusiness:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    name: str
    description: str | None
    business_type: str
    currency: str
    timezone: str
    contact_email: str | None
    contact_phone: str | None


@dataclass(frozen=True)
class ArchiveBusiness:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID


@dataclass(frozen=True)
class AddBusinessMember:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    email: str
    role: str


@dataclass(frozen=True)
class ChangeMemberRole:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    member_user_id: uuid.UUID
    role: str


@dataclass(frozen=True)
class RemoveBusinessMember:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    member_user_id: uuid.UUID


def _business_dto(business: BusinessModel) -> BusinessDTO:
    return BusinessDTO(
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
    )


async def _require_admin(
    repo: SqlAlchemyBusinessRepository, business_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    await BusinessAuthorizationService(repo.session).require(
        user_id, business_id, BusinessPermission.MANAGE_MEMBERS
    )


class UpdateBusinessHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: UpdateBusiness) -> BusinessDTO:
        async with self.uow:
            repo = SqlAlchemyBusinessRepository(self.uow.session)
            await BusinessAuthorizationService(self.uow.session).require(
                command.actor_user_id,
                command.business_id,
                BusinessPermission.MANAGE_BUSINESS,
            )
            business = await repo.get_by_id(command.business_id)
            if business is None or business.archived_at is not None:
                raise NotFoundError("Business not found")
            business.name = command.name.strip()
            business.description = command.description
            business.business_type = command.business_type
            business.currency = command.currency.upper()
            business.timezone = command.timezone
            business.contact_email = command.contact_email
            business.contact_phone = command.contact_phone
            await self.uow.commit()
            return _business_dto(business)


class ArchiveBusinessHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: ArchiveBusiness) -> None:
        async with self.uow:
            repo = SqlAlchemyBusinessRepository(self.uow.session)
            role = await BusinessAuthorizationService(self.uow.session).require(
                command.actor_user_id,
                command.business_id,
                BusinessPermission.MANAGE_BUSINESS,
            )
            if role not in {"owner", "platform_admin"}:
                raise ForbiddenError("Only the owner can archive a business")
            business = await repo.get_by_id(command.business_id)
            if business is None:
                raise NotFoundError("Business not found")
            business.archived_at = datetime.now(UTC)
            business.is_published = False
            await self.uow.commit()


class AddBusinessMemberHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: AddBusinessMember) -> None:
        if command.role not in {"admin", "editor", "viewer"}:
            raise ValidationError("Invalid member role")
        async with self.uow:
            repo = SqlAlchemyBusinessRepository(self.uow.session)
            await _require_admin(repo, command.business_id, command.actor_user_id)
            user = await SqlAlchemyUserRepository(self.uow.session).get_by_email(command.email)
            if user is None:
                raise NotFoundError("User with this email not found")
            if await repo.get_member(command.business_id, user.id):
                raise ConflictError("User is already a member")
            await repo.add_member(
                BusinessMemberModel(
                    business_id=command.business_id, user_id=user.id, role=command.role
                )
            )
            await self.uow.commit()


class ChangeMemberRoleHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: ChangeMemberRole) -> None:
        if command.role not in {"admin", "editor", "viewer"}:
            raise ValidationError("Invalid member role")
        async with self.uow:
            repo = SqlAlchemyBusinessRepository(self.uow.session)
            await _require_admin(repo, command.business_id, command.actor_user_id)
            member = await repo.get_member(command.business_id, command.member_user_id)
            if member is None:
                raise NotFoundError("Business member not found")
            if member.role == "owner":
                raise ValidationError("Owner role cannot be changed here")
            member.role = command.role
            await self.uow.commit()


class RemoveBusinessMemberHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: RemoveBusinessMember) -> None:
        async with self.uow:
            repo = SqlAlchemyBusinessRepository(self.uow.session)
            await _require_admin(repo, command.business_id, command.actor_user_id)
            member = await repo.get_member(command.business_id, command.member_user_id)
            if member is None:
                raise NotFoundError("Business member not found")
            if member.role == "owner":
                raise ValidationError("Owner cannot be removed")
            await self.uow.session.delete(member)
            await self.uow.commit()
