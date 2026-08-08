import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.modules.businesses.application.services.slugs import normalize_slug
from app.modules.catalog.application.dto.catalog import CategoryDTO, ProductDTO
from app.modules.catalog.infrastructure.models.catalog import CategoryModel, ProductModel
from app.modules.catalog.infrastructure.repositories.sqlalchemy_catalog import (
    SqlAlchemyCatalogRepository,
)
from app.modules.platform_categories.infrastructure.models.platform_category import (
    PlatformCategoryModel,
)
from app.modules.services.infrastructure.models.service import ServiceModel
from app.shared.application.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.domain.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)


@dataclass(frozen=True)
class CreateCategory:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    name: str
    slug: str


@dataclass(frozen=True)
class CreateProduct:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    name: str
    slug: str
    price: Decimal
    currency: str
    category_id: uuid.UUID | None = None
    platform_category_id: uuid.UUID | None = None
    description: str | None = None
    image_url: str | None = None
    is_published: bool = False


class CreateCategoryHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: CreateCategory) -> CategoryDTO:
        async with self.uow:
            await BusinessAuthorizationService(self.uow.session).require(
                command.actor_user_id, command.business_id, BusinessPermission.MANAGE_CONTENT
            )
            repo = SqlAlchemyCatalogRepository(self.uow.session)
            slug = normalize_slug(command.slug)
            if await repo.category_slug_exists(command.business_id, slug):
                raise ConflictError("Category slug already exists")
            category = CategoryModel(
                business_id=command.business_id, name=command.name.strip(), slug=slug
            )
            await repo.add_category(category)
            await self.uow.commit()
            return CategoryDTO(category.id, category.name, category.slug)


class CreateProductHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: CreateProduct) -> ProductDTO:
        if command.price < 0:
            raise ValidationError("Price cannot be negative")
        async with self.uow:
            await BusinessAuthorizationService(self.uow.session).require(
                command.actor_user_id, command.business_id, BusinessPermission.MANAGE_CONTENT
            )
            repo = SqlAlchemyCatalogRepository(self.uow.session)
            if command.category_id and not await repo.get_category(
                command.business_id, command.category_id
            ):
                raise ValidationError("Category does not belong to this business")
            if command.platform_category_id is not None:
                platform_category = await self.uow.session.get(
                    PlatformCategoryModel, command.platform_category_id
                )
                if platform_category is None or not platform_category.is_active:
                    raise ValidationError("Platform category does not exist or is inactive")
            slug = normalize_slug(command.slug)
            if await repo.product_slug_exists(command.business_id, slug):
                raise ConflictError("Product slug already exists")
            product = ProductModel(
                business_id=command.business_id,
                category_id=command.category_id,
                platform_category_id=command.platform_category_id,
                name=command.name.strip(),
                slug=slug,
                description=command.description,
                price=command.price,
                currency=command.currency.upper(),
                image_url=command.image_url,
                is_published=command.is_published,
            )
            await repo.add_product(product)
            await self.uow.commit()
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


@dataclass(frozen=True)
class UpdateCategory:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    category_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    image_url: str | None
    position: int
    is_visible: bool


@dataclass(frozen=True)
class DeleteCategory:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    category_id: uuid.UUID


@dataclass(frozen=True)
class UpdateProduct:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    product_id: uuid.UUID
    category_id: uuid.UUID | None
    platform_category_id: uuid.UUID | None
    name: str
    slug: str
    description: str | None
    price: Decimal
    currency: str
    image_url: str | None
    is_available: bool
    is_published: bool
    track_inventory: bool
    stock_quantity: int | None


@dataclass(frozen=True)
class ArchiveProduct:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    product_id: uuid.UUID


async def _require_catalog_access(
    uow: SqlAlchemyUnitOfWork, business_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    await BusinessAuthorizationService(uow.session).require(
        user_id, business_id, BusinessPermission.MANAGE_CONTENT
    )


class UpdateCategoryHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: UpdateCategory) -> CategoryDTO:
        async with self.uow:
            await _require_catalog_access(self.uow, command.business_id, command.actor_user_id)
            repo = SqlAlchemyCatalogRepository(self.uow.session)
            category = await repo.get_category(command.business_id, command.category_id)
            if category is None:
                raise NotFoundError("Category not found")
            slug = normalize_slug(command.slug)
            existing = await self.uow.session.scalar(
                select(CategoryModel.id).where(
                    CategoryModel.business_id == command.business_id,
                    CategoryModel.slug == slug,
                    CategoryModel.id != category.id,
                )
            )
            if existing:
                raise ConflictError("Category slug already exists")
            category.name = command.name.strip()
            category.slug = slug
            category.description = command.description
            category.image_url = command.image_url
            category.position = command.position
            category.is_visible = command.is_visible
            await self.uow.commit()
            return CategoryDTO(category.id, category.name, category.slug)


class DeleteCategoryHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: DeleteCategory) -> None:
        async with self.uow:
            await _require_catalog_access(self.uow, command.business_id, command.actor_user_id)
            repo = SqlAlchemyCatalogRepository(self.uow.session)
            category = await repo.get_category(command.business_id, command.category_id)
            if category is None:
                raise NotFoundError("Category not found")
            products = await self.uow.session.scalar(
                select(ProductModel.id).where(ProductModel.category_id == category.id).limit(1)
            )
            if products:
                raise ConflictError("Category cannot be deleted while it contains products")
            services = await self.uow.session.scalar(
                select(ServiceModel.id).where(ServiceModel.category_id == category.id).limit(1)
            )
            if services:
                raise ConflictError("Category cannot be deleted while it contains services")
            await self.uow.session.delete(category)
            await self.uow.commit()


class UpdateProductHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: UpdateProduct) -> ProductDTO:
        if command.price < 0:
            raise ValidationError("Price cannot be negative")
        async with self.uow:
            await _require_catalog_access(self.uow, command.business_id, command.actor_user_id)
            repo = SqlAlchemyCatalogRepository(self.uow.session)
            product = await repo.get_product(command.business_id, command.product_id)
            if product is None or product.archived_at is not None:
                raise NotFoundError("Product not found")
            if command.category_id and not await repo.get_category(
                command.business_id, command.category_id
            ):
                raise ValidationError("Category does not belong to this business")
            if command.platform_category_id is not None:
                platform_category = await self.uow.session.get(
                    PlatformCategoryModel, command.platform_category_id
                )
                if platform_category is None or not platform_category.is_active:
                    raise ValidationError("Platform category does not exist or is inactive")
            slug = normalize_slug(command.slug)
            existing = await self.uow.session.scalar(
                select(ProductModel.id).where(
                    ProductModel.business_id == command.business_id,
                    ProductModel.slug == slug,
                    ProductModel.id != product.id,
                )
            )
            if existing:
                raise ConflictError("Product slug already exists")
            for field in (
                "category_id",
                "platform_category_id",
                "description",
                "price",
                "image_url",
                "is_available",
                "is_published",
                "track_inventory",
                "stock_quantity",
            ):
                setattr(product, field, getattr(command, field))
            product.name = command.name.strip()
            product.slug = slug
            product.currency = command.currency.upper()
            await self.uow.commit()
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


class ArchiveProductHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: ArchiveProduct) -> None:
        async with self.uow:
            await _require_catalog_access(self.uow, command.business_id, command.actor_user_id)
            product = await SqlAlchemyCatalogRepository(self.uow.session).get_product(
                command.business_id, command.product_id
            )
            if product is None:
                raise NotFoundError("Product not found")
            product.archived_at = datetime.now(UTC)
            product.is_published = False
            product.is_available = False
            await self.uow.commit()
