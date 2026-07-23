import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field

from app.modules.auth.api.routes import get_current_user
from app.modules.auth.application.dto.auth import UserDTO
from app.modules.sites.application.commands.sites import (
    AddSiteSection,
    DeleteSiteSection,
    PublishSite,
    UpdateSiteSection,
    UpdateSiteSettings,
)
from app.modules.sites.application.dto.sites import PublicSiteDTO, SectionDTO
from app.modules.sites.application.queries.sites import GetManagedSite, GetPublicBusinessSite
from app.shared.application.cqrs import CommandBus, QueryBus
from app.shared.infrastructure.dependencies import get_command_bus, get_query_bus

admin_router = APIRouter(prefix="/businesses/{business_id}/site", tags=["sites"])
public_router = APIRouter(prefix="/public/businesses", tags=["public"])


class AddSectionRequest(BaseModel):
    section_type: str
    position: int = Field(ge=0)
    content: dict[str, object]


class UpdateSectionRequest(AddSectionRequest):
    is_visible: bool = True


class UpdateSiteRequest(BaseModel):
    favicon_url: str | None = None
    palette: dict[str, object] = Field(default_factory=dict)
    typography: dict[str, object] = Field(default_factory=dict)
    seo: dict[str, object] = Field(default_factory=dict)


@admin_router.post("/sections", response_model=SectionDTO, status_code=status.HTTP_201_CREATED)
async def add_section(
    business_id: uuid.UUID,
    body: AddSectionRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> SectionDTO:
    return await bus.dispatch(AddSiteSection(user.id, business_id, **body.model_dump()))


@admin_router.post("/publish", status_code=status.HTTP_204_NO_CONTENT)
async def publish_site(
    business_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> Response:
    await bus.dispatch(PublishSite(user.id, business_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.get("", response_model=PublicSiteDTO)
async def get_site(
    business_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> PublicSiteDTO:
    return await bus.dispatch(GetManagedSite(user.id, business_id))


@admin_router.put("", status_code=status.HTTP_204_NO_CONTENT)
async def update_site(
    business_id: uuid.UUID,
    body: UpdateSiteRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> Response:
    await bus.dispatch(UpdateSiteSettings(user.id, business_id, **body.model_dump()))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.put("/sections/{section_id}", response_model=SectionDTO)
async def update_section(
    business_id: uuid.UUID,
    section_id: uuid.UUID,
    body: UpdateSectionRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> SectionDTO:
    return await bus.dispatch(
        UpdateSiteSection(user.id, business_id, section_id, **body.model_dump())
    )


@admin_router.delete("/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    business_id: uuid.UUID,
    section_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> Response:
    await bus.dispatch(DeleteSiteSection(user.id, business_id, section_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@public_router.get("/{business_slug}", response_model=PublicSiteDTO)
async def get_public_site(
    business_slug: str, bus: Annotated[QueryBus, Depends(get_query_bus)]
) -> PublicSiteDTO:
    return await bus.dispatch(GetPublicBusinessSite(business_slug))
