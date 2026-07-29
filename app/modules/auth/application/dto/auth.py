import uuid
from dataclasses import dataclass

from app.modules.businesses.application.dto.business import BusinessDTO


@dataclass(frozen=True)
class UserDTO:
    id: uuid.UUID
    email: str
    full_name: str
    is_platform_admin: bool


@dataclass(frozen=True)
class TokenPairDTO:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@dataclass(frozen=True)
class BusinessOnboardingDTO:
    user: UserDTO
    business: BusinessDTO
    tokens: TokenPairDTO
