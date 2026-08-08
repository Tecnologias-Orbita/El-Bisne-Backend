import uuid
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ServiceDTO:
    id: uuid.UUID
    category_id: uuid.UUID | None
    platform_category_id: uuid.UUID | None
    name: str
    slug: str
    description: str | None
    price: Decimal | None
    currency: str | None
    duration_minutes: int | None
    image_url: str | None
    is_available: bool
    is_published: bool = False
