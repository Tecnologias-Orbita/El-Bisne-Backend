import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.infrastructure.models.user import UserModel
from app.modules.businesses.application.dto.business import (
    BusinessDTO,
    BusinessMemberDTO,
    BusinessSiteDTO,
)
from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.modules.businesses.infrastructure.models.business import BusinessMemberModel, BusinessModel
from app.modules.businesses.infrastructure.repositories.sqlalchemy_businesses import (
    SqlAlchemyBusinessRepository,
)
from app.modules.sites.infrastructure.models.site import BusinessSiteModel
from app.shared.domain.exceptions import NotFoundError


@dataclass(frozen=True)
class ListManagedBusinesses:
    user_id: uuid.UUID


class ListManagedBusinessesHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: ListManagedBusinesses) -> list[BusinessDTO]:
        authorization = BusinessAuthorizationService(self.session)
        if await authorization.is_platform_admin(query.user_id):
            rows = (
                await self.session.execute(
                    select(BusinessModel, BusinessSiteModel)
                    .outerjoin(BusinessSiteModel, BusinessSiteModel.business_id == BusinessModel.id)
                    .where(BusinessModel.archived_at.is_(None))
                    .order_by(BusinessModel.name)
                )
            ).all()
        else:
            rows = (
                await self.session.execute(
                    select(BusinessModel, BusinessSiteModel)
                    .join(BusinessMemberModel)
                    .outerjoin(BusinessSiteModel, BusinessSiteModel.business_id == BusinessModel.id)
                    .where(
                        BusinessMemberModel.user_id == query.user_id,
                        BusinessModel.archived_at.is_(None),
                    )
                    .order_by(BusinessModel.name)
                )
            ).all()
        return [
            BusinessDTO(
                item.id,
                item.name,
                item.slug,
                item.description,
                item.business_type,
                item.currency,
                item.timezone,
                item.contact_email,
                item.contact_phone,
                item.is_published,
                item.platform_category_id,
                BusinessSiteDTO(
                    site.hero_image_url if site else None,
                    site.logo_url if site else None,
                ),
            )
            for item, site in rows
        ]


@dataclass(frozen=True)
class GetBusiness:
    user_id: uuid.UUID
    business_id: uuid.UUID


@dataclass(frozen=True)
class ListBusinessMembers:
    user_id: uuid.UUID
    business_id: uuid.UUID


class GetBusinessHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: GetBusiness) -> BusinessDTO:
        repo = SqlAlchemyBusinessRepository(self.session)
        await BusinessAuthorizationService(self.session).require(
            query.user_id, query.business_id, BusinessPermission.VIEW
        )
        business = await repo.get_by_id(query.business_id)
        if business is None or business.archived_at is not None:
            raise NotFoundError("Business not found")
        site = await self.session.scalar(
            select(BusinessSiteModel).where(BusinessSiteModel.business_id == business.id)
        )
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
            business.platform_category_id,
            BusinessSiteDTO(
                site.hero_image_url if site else None,
                site.logo_url if site else None,
            ),
        )


class ListBusinessMembersHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: ListBusinessMembers) -> list[BusinessMemberDTO]:
        await BusinessAuthorizationService(self.session).require(
            query.user_id, query.business_id, BusinessPermission.MANAGE_MEMBERS
        )
        rows = (
            await self.session.execute(
                select(BusinessMemberModel, UserModel)
                .join(UserModel, UserModel.id == BusinessMemberModel.user_id)
                .where(BusinessMemberModel.business_id == query.business_id)
                .order_by(UserModel.full_name)
            )
        ).all()
        return [
            BusinessMemberDTO(member.id, user.id, user.email, user.full_name, member.role)
            for member, user in rows
        ]
