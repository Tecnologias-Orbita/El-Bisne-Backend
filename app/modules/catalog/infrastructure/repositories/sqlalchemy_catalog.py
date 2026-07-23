import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.infrastructure.models.catalog import CategoryModel, ProductModel


class SqlAlchemyCatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_category(self, category: CategoryModel) -> None:
        self.session.add(category)
        await self.session.flush()

    async def add_product(self, product: ProductModel) -> None:
        self.session.add(product)
        await self.session.flush()

    async def get_category(
        self, business_id: uuid.UUID, category_id: uuid.UUID
    ) -> CategoryModel | None:
        return await self.session.scalar(
            select(CategoryModel).where(
                CategoryModel.id == category_id, CategoryModel.business_id == business_id
            )
        )

    async def get_product(
        self, business_id: uuid.UUID, product_id: uuid.UUID
    ) -> ProductModel | None:
        return await self.session.scalar(
            select(ProductModel).where(
                ProductModel.id == product_id, ProductModel.business_id == business_id
            )
        )

    async def list_categories(self, business_id: uuid.UUID) -> list[CategoryModel]:
        return list(
            await self.session.scalars(
                select(CategoryModel)
                .where(CategoryModel.business_id == business_id)
                .order_by(CategoryModel.position, CategoryModel.name)
            )
        )

    async def list_products(self, business_id: uuid.UUID) -> list[ProductModel]:
        return list(
            await self.session.scalars(
                select(ProductModel)
                .where(ProductModel.business_id == business_id, ProductModel.archived_at.is_(None))
                .order_by(ProductModel.name)
            )
        )

    async def category_slug_exists(self, business_id: uuid.UUID, slug: str) -> bool:
        return (
            await self.session.scalar(
                select(CategoryModel.id).where(
                    CategoryModel.business_id == business_id, CategoryModel.slug == slug
                )
            )
            is not None
        )

    async def product_slug_exists(self, business_id: uuid.UUID, slug: str) -> bool:
        return (
            await self.session.scalar(
                select(ProductModel.id).where(
                    ProductModel.business_id == business_id, ProductModel.slug == slug
                )
            )
            is not None
        )

    async def list_public_products(self, business_id: uuid.UUID) -> list[ProductModel]:
        result = await self.session.scalars(
            select(ProductModel)
            .where(
                ProductModel.business_id == business_id,
                ProductModel.is_published.is_(True),
                ProductModel.archived_at.is_(None),
            )
            .order_by(ProductModel.name)
        )
        return list(result)

    async def get_available_products(
        self, business_id: uuid.UUID, product_ids: list[uuid.UUID]
    ) -> list[ProductModel]:
        result = await self.session.scalars(
            select(ProductModel).where(
                ProductModel.business_id == business_id,
                ProductModel.id.in_(product_ids),
                ProductModel.is_published.is_(True),
                ProductModel.is_available.is_(True),
                ProductModel.archived_at.is_(None),
            )
        )
        return list(result)
