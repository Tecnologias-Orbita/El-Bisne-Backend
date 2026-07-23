import uuid
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CategoryDTO:
    id: uuid.UUID
    name: str
    slug: str


@dataclass(frozen=True)
class ProductDTO:
    id: uuid.UUID
    category_id: uuid.UUID | None
    name: str
    slug: str
    product_type: str
    description: str | None
    price: Decimal
    currency: str
    image_url: str | None
    is_available: bool


@dataclass(frozen=True)
class CatalogDTO:
    business_id: uuid.UUID
    business_name: str
    items: list[ProductDTO]
    total: int
    page: int = 1
    page_size: int = 100
