import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, EmailStr, Field

from app.modules.auth.api.routes import get_current_user
from app.modules.auth.application.dto.auth import UserDTO
from app.modules.businesses.application.commands.businesses import (
    AddBusinessMember,
    ArchiveBusiness,
    ChangeMemberRole,
    CreateBusiness,
    RemoveBusinessMember,
    UpdateBusiness,
)
from app.modules.businesses.application.dto.business import BusinessDTO, BusinessMemberDTO
from app.modules.businesses.application.queries.businesses import (
    GetBusiness,
    ListBusinessMembers,
    ListManagedBusinesses,
)
from app.shared.application.cqrs import CommandBus, QueryBus
from app.shared.infrastructure.dependencies import get_command_bus, get_query_bus

router = APIRouter(prefix="/businesses", tags=["businesses"])


class CreateBusinessRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=3, max_length=100)
    business_type: str = Field(min_length=2, max_length=50)
    description: str | None = None
    currency: str = Field(default="USD", min_length=3, max_length=3)
    timezone: str = "America/Havana"
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=32)


class UpdateBusinessRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    business_type: str = Field(min_length=2, max_length=50)
    currency: str = Field(min_length=3, max_length=3)
    timezone: str
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=32)


class MemberRequest(BaseModel):
    email: EmailStr
    role: str


class RoleRequest(BaseModel):
    role: str


@router.post("", response_model=BusinessDTO, status_code=status.HTTP_201_CREATED)
async def create_business(
    body: CreateBusinessRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> BusinessDTO:
    return await bus.dispatch(CreateBusiness(actor_user_id=user.id, **body.model_dump()))


@router.get("", response_model=list[BusinessDTO])
async def list_businesses(
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> list[BusinessDTO]:
    return await bus.dispatch(ListManagedBusinesses(user.id))


@router.get("/{business_id}", response_model=BusinessDTO)
async def get_business(
    business_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> BusinessDTO:
    return await bus.dispatch(GetBusiness(user.id, business_id))


@router.put("/{business_id}", response_model=BusinessDTO)
async def update_business(
    business_id: uuid.UUID,
    body: UpdateBusinessRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> BusinessDTO:
    return await bus.dispatch(UpdateBusiness(user.id, business_id, **body.model_dump()))


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_business(
    business_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> Response:
    await bus.dispatch(ArchiveBusiness(user.id, business_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{business_id}/members", response_model=list[BusinessMemberDTO])
async def list_members(
    business_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> list[BusinessMemberDTO]:
    return await bus.dispatch(ListBusinessMembers(user.id, business_id))


@router.post("/{business_id}/members", status_code=status.HTTP_204_NO_CONTENT)
async def add_member(
    business_id: uuid.UUID,
    body: MemberRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> Response:
    await bus.dispatch(AddBusinessMember(user.id, business_id, str(body.email), body.role))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{business_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def change_member_role(
    business_id: uuid.UUID,
    member_user_id: uuid.UUID,
    body: RoleRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> Response:
    await bus.dispatch(ChangeMemberRole(user.id, business_id, member_user_id, body.role))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{business_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    business_id: uuid.UUID,
    member_user_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> Response:
    await bus.dispatch(RemoveBusinessMember(user.id, business_id, member_user_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
