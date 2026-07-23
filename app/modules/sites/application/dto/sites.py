import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class SectionDTO:
    id: uuid.UUID
    section_type: str
    position: int
    content: dict[str, object]
    is_visible: bool


@dataclass(frozen=True)
class PublicSiteDTO:
    business_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    favicon_url: str | None
    palette: dict[str, object]
    typography: dict[str, object]
    seo: dict[str, object]
    sections: list[SectionDTO]
