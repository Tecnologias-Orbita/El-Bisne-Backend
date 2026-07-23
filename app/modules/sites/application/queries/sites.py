import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.modules.businesses.infrastructure.repositories.sqlalchemy_businesses import (
    SqlAlchemyBusinessRepository,
)
from app.modules.sites.application.dto.sites import PublicSiteDTO, SectionDTO
from app.modules.sites.infrastructure.models.site import BusinessSiteModel, SiteSectionModel
from app.shared.domain.exceptions import NotFoundError


@dataclass(frozen=True)
class GetPublicBusinessSite:
    business_slug: str


class GetPublicBusinessSiteHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: GetPublicBusinessSite) -> PublicSiteDTO:
        business = await SqlAlchemyBusinessRepository(self.session).get_by_slug(query.business_slug)
        if business is None or not business.is_published or business.archived_at is not None:
            raise NotFoundError("Business not found")
        site = await self.session.scalar(
            select(BusinessSiteModel).where(
                BusinessSiteModel.business_id == business.id,
                BusinessSiteModel.is_published.is_(True),
            )
        )
        if site is None:
            raise NotFoundError("Published site not found")
        result = await self.session.scalars(
            select(SiteSectionModel)
            .where(SiteSectionModel.site_id == site.id, SiteSectionModel.is_visible.is_(True))
            .order_by(SiteSectionModel.position)
        )
        sections = [
            SectionDTO(item.id, item.section_type, item.position, item.content, item.is_visible)
            for item in result
        ]
        return PublicSiteDTO(
            business.id,
            business.name,
            business.slug,
            business.description,
            site.favicon_url,
            site.palette,
            site.typography,
            site.seo,
            sections,
        )


@dataclass(frozen=True)
class GetManagedSite:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID


class GetManagedSiteHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: GetManagedSite) -> PublicSiteDTO:
        repo = SqlAlchemyBusinessRepository(self.session)
        await BusinessAuthorizationService(self.session).require(
            query.actor_user_id, query.business_id, BusinessPermission.VIEW
        )
        business = await repo.get_by_id(query.business_id)
        site = await self.session.scalar(
            select(BusinessSiteModel).where(BusinessSiteModel.business_id == query.business_id)
        )
        if business is None or site is None:
            raise NotFoundError("Business site not found")
        result = await self.session.scalars(
            select(SiteSectionModel)
            .where(SiteSectionModel.site_id == site.id)
            .order_by(SiteSectionModel.position)
        )
        return PublicSiteDTO(
            business.id,
            business.name,
            business.slug,
            business.description,
            site.favicon_url,
            site.palette,
            site.typography,
            site.seo,
            [SectionDTO(x.id, x.section_type, x.position, x.content, x.is_visible) for x in result],
        )
