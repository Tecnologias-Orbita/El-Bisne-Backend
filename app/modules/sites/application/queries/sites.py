import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.businesses.application.dto.business import BusinessDTO, BusinessSiteDTO
from app.modules.businesses.infrastructure.models.business import BusinessModel
from app.modules.businesses.infrastructure.repositories.sqlalchemy_businesses import (
    SqlAlchemyBusinessRepository,
)
from app.modules.catalog.infrastructure.models.catalog import ProductModel
from app.modules.platform_categories.application.dto.platform_category import PlatformCategoryDTO
from app.modules.platform_categories.infrastructure.models.platform_category import (
    PlatformCategoryModel,
)
from app.modules.services.infrastructure.models.service import ServiceModel
from app.modules.sites.infrastructure.models.site import BusinessSiteModel
from app.shared.domain.exceptions import NotFoundError


@dataclass(frozen=True)
class GetPublicBusiness:
    business_slug: str


@dataclass(frozen=True)
class DiscoverPlatform:
    search: str | None = None
    platform_category_id: uuid.UUID | None = None


@dataclass(frozen=True)
class DiscoveryBusinessDTO:
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    sells_online: bool
    platform_category_id: uuid.UUID | None
    hero_image_url: str | None
    logo_url: str | None


@dataclass(frozen=True)
class DiscoveryProductDTO:
    id: uuid.UUID
    business_id: uuid.UUID
    business_name: str
    business_slug: str
    platform_category_id: uuid.UUID | None
    name: str
    slug: str
    description: str | None
    price: Decimal
    currency: str
    image_url: str | None
    is_available: bool


@dataclass(frozen=True)
class DiscoveryServiceDTO:
    id: uuid.UUID
    business_id: uuid.UUID
    business_name: str
    business_slug: str
    platform_category_id: uuid.UUID | None
    name: str
    slug: str
    description: str | None
    price: Decimal | None
    currency: str | None
    duration_minutes: int | None
    image_url: str | None


@dataclass(frozen=True)
class PlatformDiscoveryDTO:
    categories: list[PlatformCategoryDTO]
    businesses: list[DiscoveryBusinessDTO]
    products: list[DiscoveryProductDTO]
    services: list[DiscoveryServiceDTO]


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
            business.sells_online,
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


class DiscoverPlatformHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: DiscoverPlatform) -> PlatformDiscoveryDTO:
        category_models = list(
            await self.session.scalars(
                select(PlatformCategoryModel)
                .where(PlatformCategoryModel.is_active.is_(True))
                .order_by(PlatformCategoryModel.name)
            )
        )

        business_statement = select(BusinessModel).where(
            BusinessModel.is_published.is_(True),
            BusinessModel.archived_at.is_(None),
        )
        if query.platform_category_id:
            business_statement = business_statement.where(
                BusinessModel.platform_category_id == query.platform_category_id
            )
        if query.search:
            term = f"%{query.search.strip()}%"
            business_statement = business_statement.where(
                or_(BusinessModel.name.ilike(term), BusinessModel.description.ilike(term))
            )
        businesses = list(
            await self.session.scalars(business_statement.order_by(BusinessModel.name))
        )
        business_ids = [business.id for business in businesses]
        sites = (
            list(
                await self.session.scalars(
                    select(BusinessSiteModel).where(BusinessSiteModel.business_id.in_(business_ids))
                )
            )
            if business_ids
            else []
        )
        sites_by_business = {site.business_id: site for site in sites}

        product_statement = (
            select(ProductModel, BusinessModel)
            .join(BusinessModel, BusinessModel.id == ProductModel.business_id)
            .where(
                ProductModel.is_published.is_(True),
                ProductModel.archived_at.is_(None),
                BusinessModel.is_published.is_(True),
                BusinessModel.archived_at.is_(None),
            )
        )
        if query.platform_category_id:
            product_statement = product_statement.where(
                ProductModel.platform_category_id == query.platform_category_id
            )
        if query.search:
            term = f"%{query.search.strip()}%"
            product_statement = product_statement.where(
                or_(ProductModel.name.ilike(term), ProductModel.description.ilike(term))
            )
        product_rows = list(
            (await self.session.execute(product_statement.order_by(ProductModel.name))).all()
        )

        service_statement = (
            select(ServiceModel, BusinessModel)
            .join(BusinessModel, BusinessModel.id == ServiceModel.business_id)
            .where(
                ServiceModel.is_published.is_(True),
                ServiceModel.is_available.is_(True),
                ServiceModel.archived_at.is_(None),
                BusinessModel.is_published.is_(True),
                BusinessModel.archived_at.is_(None),
            )
        )
        if query.platform_category_id:
            service_statement = service_statement.where(
                ServiceModel.platform_category_id == query.platform_category_id
            )
        if query.search:
            term = f"%{query.search.strip()}%"
            service_statement = service_statement.where(
                or_(ServiceModel.name.ilike(term), ServiceModel.description.ilike(term))
            )
        service_rows = list(
            (await self.session.execute(service_statement.order_by(ServiceModel.name))).all()
        )

        return PlatformDiscoveryDTO(
            categories=[
                PlatformCategoryDTO(
                    category.id,
                    category.name,
                    category.slug,
                    category.description,
                    category.is_active,
                )
                for category in category_models
            ],
            businesses=[
                DiscoveryBusinessDTO(
                    business.id,
                    business.name,
                    business.slug,
                    business.description,
                    business.sells_online,
                    business.platform_category_id,
                    sites_by_business[business.id].hero_image_url
                    if business.id in sites_by_business
                    else None,
                    sites_by_business[business.id].logo_url
                    if business.id in sites_by_business
                    else None,
                )
                for business in businesses
            ],
            products=[
                DiscoveryProductDTO(
                    product.id,
                    business.id,
                    business.name,
                    business.slug,
                    product.platform_category_id,
                    product.name,
                    product.slug,
                    product.description,
                    product.price,
                    product.currency,
                    product.image_url,
                    product.is_available,
                )
                for product, business in product_rows
            ],
            services=[
                DiscoveryServiceDTO(
                    service.id,
                    business.id,
                    business.name,
                    business.slug,
                    service.platform_category_id,
                    service.name,
                    service.slug,
                    service.description,
                    service.price,
                    service.currency,
                    service.duration_minutes,
                    service.image_url,
                )
                for service, business in service_rows
            ],
        )
