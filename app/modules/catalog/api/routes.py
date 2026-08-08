import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field, HttpUrl

from app.modules.auth.api.routes import get_current_user
from app.modules.auth.application.dto.auth import UserDTO
from app.modules.catalog.application.commands.catalog import (
    ArchiveProduct,
    CreateCategory,
    CreateProduct,
    DeleteCategory,
    UpdateCategory,
    UpdateProduct,
)
from app.modules.catalog.application.dto.catalog import CatalogDTO, CategoryDTO, ProductDTO
from app.modules.catalog.application.queries.catalog import (
    GetProduct,
    GetPublicCatalog,
    ListCategories,
    ListProducts,
)
from app.shared.application.cqrs import CommandBus, QueryBus
from app.shared.infrastructure.dependencies import get_command_bus, get_query_bus

admin_router = APIRouter(prefix="/businesses/{business_id}/catalog", tags=["catalog"])
public_router = APIRouter(prefix="/public/businesses", tags=["public"])


class CreateCategoryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=3, max_length=100)


class CreateProductRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=3, max_length=120)
    price: Decimal = Field(ge=0, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    category_id: uuid.UUID | None = None
    platform_category_id: uuid.UUID | None = None
    description: str | None = None
    image_url: HttpUrl | None = None
    is_published: bool = False


class UpdateCategoryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=3, max_length=100)
    description: str | None = None
    image_url: HttpUrl | None = None
    position: int = Field(default=0, ge=0)
    is_visible: bool = True


class UpdateProductRequest(BaseModel):
    category_id: uuid.UUID | None = None
    platform_category_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=3, max_length=120)
    description: str | None = None
    price: Decimal = Field(ge=0, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    image_url: HttpUrl | None = None
    is_available: bool = True
    is_published: bool = False
    track_inventory: bool = False
    stock_quantity: int | None = Field(default=None, ge=0)


@admin_router.post("/categories", response_model=CategoryDTO, status_code=status.HTTP_201_CREATED)
async def create_category(
    business_id: uuid.UUID,
    body: CreateCategoryRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> CategoryDTO:
    return await bus.dispatch(CreateCategory(user.id, business_id, **body.model_dump()))


@admin_router.post("/products", response_model=ProductDTO, status_code=status.HTTP_201_CREATED)
async def create_product(
    business_id: uuid.UUID,
    body: CreateProductRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> ProductDTO:
    data = body.model_dump(mode="json")
    data["price"] = body.price
    data["category_id"] = body.category_id
    data["platform_category_id"] = body.platform_category_id
    return await bus.dispatch(CreateProduct(user.id, business_id, **data))


@admin_router.get("/categories", response_model=list[CategoryDTO])
async def list_categories(
    business_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> list[CategoryDTO]:
    return await bus.dispatch(ListCategories(user.id, business_id))


@admin_router.put("/categories/{category_id}", response_model=CategoryDTO)
async def update_category(
    business_id: uuid.UUID,
    category_id: uuid.UUID,
    body: UpdateCategoryRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> CategoryDTO:
    data = body.model_dump(mode="json")
    return await bus.dispatch(UpdateCategory(user.id, business_id, category_id, **data))


@admin_router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    business_id: uuid.UUID,
    category_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> Response:
    await bus.dispatch(DeleteCategory(user.id, business_id, category_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.get("/products", response_model=list[ProductDTO])
async def list_products(
    business_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> list[ProductDTO]:
    return await bus.dispatch(ListProducts(user.id, business_id))


@admin_router.get("/products/{product_id}", response_model=ProductDTO)
async def get_product(
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> ProductDTO:
    return await bus.dispatch(GetProduct(user.id, business_id, product_id))


@admin_router.put("/products/{product_id}", response_model=ProductDTO)
async def update_product(
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    body: UpdateProductRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> ProductDTO:
    data = body.model_dump(mode="json")
    data["price"] = body.price
    data["category_id"] = body.category_id
    data["platform_category_id"] = body.platform_category_id
    return await bus.dispatch(UpdateProduct(user.id, business_id, product_id, **data))


@admin_router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_product(
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> Response:
    await bus.dispatch(ArchiveProduct(user.id, business_id, product_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@public_router.get("/{business_slug}/catalog", response_model=CatalogDTO)
async def get_public_catalog(
    business_slug: str, bus: Annotated[QueryBus, Depends(get_query_bus)]
) -> CatalogDTO:
    return await bus.dispatch(GetPublicCatalog(business_slug))
