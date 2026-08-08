import uuid
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CategoryDTO:
    id: uuid.UUID
    name: str
    slug: str
    image_url: str | None
    description: str | None = None
    position: int = 0
    is_visible: bool = True


@dataclass(frozen=True)
class ProductDTO:
    id: uuid.UUID
    category_id: uuid.UUID | None
    platform_category_id: uuid.UUID | None
    name: str
    slug: str
    description: str | None
    price: Decimal
    currency: str
    image_url: str | None
    is_available: bool
    is_published: bool = False
    track_inventory: bool = False
    stock_quantity: int | None = None


@dataclass(frozen=True)
class CatalogDTO:
    business_id: uuid.UUID
    business_name: str
    categories: list[CategoryDTO]
    items: list[ProductDTO]
    total: int
    page: int = 1
    page_size: int = 100
