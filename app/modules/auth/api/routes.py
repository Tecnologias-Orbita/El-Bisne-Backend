import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from app.modules.auth.application.commands.auth import LoginUser, RefreshSession, RegisterUser
from app.modules.auth.application.dto.auth import UserDTO
from app.modules.auth.application.queries.users import GetCurrentUser
from app.shared.application.cqrs import CommandBus, QueryBus
from app.shared.infrastructure.dependencies import get_command_bus, get_query_bus
from app.shared.infrastructure.security import decode_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=160)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


@router.post("/register", response_model=UserDTO, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest, bus: Annotated[CommandBus, Depends(get_command_bus)]
) -> UserDTO:
    return await bus.dispatch(RegisterUser(**body.model_dump()))


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, bus: Annotated[CommandBus, Depends(get_command_bus)]
) -> TokenResponse:
    return TokenResponse.model_validate(
        await bus.dispatch(LoginUser(**body.model_dump())), from_attributes=True
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest, bus: Annotated[CommandBus, Depends(get_command_bus)]
) -> TokenResponse:
    return TokenResponse.model_validate(
        await bus.dispatch(RefreshSession(body.refresh_token)), from_attributes=True
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> UserDTO:
    payload = decode_access_token(credentials.credentials)
    return await bus.dispatch(GetCurrentUser(uuid.UUID(payload["sub"])))


@router.get("/me", response_model=UserDTO)
async def me(user: Annotated[UserDTO, Depends(get_current_user)]) -> UserDTO:
    return user
