import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.modules.businesses.infrastructure.repositories.sqlalchemy_businesses import (
    SqlAlchemyBusinessRepository,
)
from app.modules.catalog.application.dto.catalog import CatalogDTO, CategoryDTO, ProductDTO
from app.modules.catalog.infrastructure.repositories.sqlalchemy_catalog import (
    SqlAlchemyCatalogRepository,
)
from app.shared.domain.exceptions import NotFoundError


@dataclass(frozen=True)
class GetPublicCatalog:
    business_slug: str


class GetPublicCatalogHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: GetPublicCatalog) -> CatalogDTO:
        business = await SqlAlchemyBusinessRepository(self.session).get_by_slug(query.business_slug)
        if business is None or not business.is_published or business.archived_at is not None:
            raise NotFoundError("Business not found")
        repository = SqlAlchemyCatalogRepository(self.session)
        products = await repository.list_public_products(business.id)
        categories = [
            CategoryDTO(category.id, category.name, category.slug, category.image_url)
            for category in await repository.list_categories(business.id)
            if category.is_visible
        ]
        items = [
            ProductDTO(
                product.id,
                product.category_id,
                product.platform_category_id,
                product.name,
                product.slug,
                product.description,
                product.price,
                product.currency,
                product.image_url,
                product.is_available,
            )
            for product in products
        ]
        return CatalogDTO(business.id, business.name, categories, items, len(items))


@dataclass(frozen=True)
class ListCategories:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID


@dataclass(frozen=True)
class ListProducts:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID


@dataclass(frozen=True)
class GetProduct:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    product_id: uuid.UUID


async def _require_member(
    session: AsyncSession, business_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    await BusinessAuthorizationService(session).require(
        user_id, business_id, BusinessPermission.VIEW
    )


def _product_dto(product: object) -> ProductDTO:
    return ProductDTO(
        product.id,
        product.category_id,
        product.platform_category_id,
        product.name,
        product.slug,
        product.description,
        product.price,
        product.currency,
        product.image_url,
        product.is_available,
    )


class ListCategoriesHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: ListCategories) -> list[CategoryDTO]:
        await _require_member(self.session, query.business_id, query.actor_user_id)
        items = await SqlAlchemyCatalogRepository(self.session).list_categories(query.business_id)
        return [CategoryDTO(item.id, item.name, item.slug, item.image_url) for item in items]


class ListProductsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: ListProducts) -> list[ProductDTO]:
        await _require_member(self.session, query.business_id, query.actor_user_id)
        items = await SqlAlchemyCatalogRepository(self.session).list_products(query.business_id)
        return [_product_dto(item) for item in items]


class GetProductHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: GetProduct) -> ProductDTO:
        await _require_member(self.session, query.business_id, query.actor_user_id)
        item = await SqlAlchemyCatalogRepository(self.session).get_product(
            query.business_id, query.product_id
        )
        if item is None or item.archived_at is not None:
            raise NotFoundError("Product not found")
        return _product_dto(item)
