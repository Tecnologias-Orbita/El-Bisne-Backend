import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class BusinessDTO:
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    business_type: str
    currency: str
    timezone: str
    contact_email: str | None
    contact_phone: str | None
    is_published: bool


@dataclass(frozen=True)
class BusinessMemberDTO:
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
