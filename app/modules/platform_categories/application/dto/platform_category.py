import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformCategoryDTO:
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    is_active: bool
