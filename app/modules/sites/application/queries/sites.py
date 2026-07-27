from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.businesses.application.dto.business import BusinessDTO, BusinessSiteDTO
from app.modules.businesses.infrastructure.repositories.sqlalchemy_businesses import (
    SqlAlchemyBusinessRepository,
)
from app.modules.sites.infrastructure.models.site import BusinessSiteModel
from app.shared.domain.exceptions import NotFoundError


@dataclass(frozen=True)
class GetPublicBusiness:
    business_slug: str


class GetPublicBusinessHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: GetPublicBusiness) -> BusinessDTO:
        business = await SqlAlchemyBusinessRepository(self.session).get_by_slug(query.business_slug)
        if business is None or not business.is_published or business.archived_at is not None:
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
            BusinessSiteDTO(
                site.hero_image_url if site else None,
                site.logo_url if site else None,
            ),
        )
