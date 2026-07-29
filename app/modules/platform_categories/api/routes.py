import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field

from app.modules.auth.api.routes import get_current_user
from app.modules.auth.application.dto.auth import UserDTO
from app.modules.platform_categories.application.commands.platform_categories import (
    CreatePlatformCategory,
    DeletePlatformCategory,
    UpdatePlatformCategory,
)
from app.modules.platform_categories.application.dto.platform_category import PlatformCategoryDTO
from app.modules.platform_categories.application.queries.platform_categories import (
    ListPlatformCategories,
)
from app.shared.application.cqrs import CommandBus, QueryBus
from app.shared.infrastructure.dependencies import get_command_bus, get_query_bus

router = APIRouter(prefix="/platform/categories", tags=["platform-categories"])
admin_router = APIRouter(prefix="/platform/admin/categories", tags=["platform-categories"])


class PlatformCategoryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = None
    is_active: bool = True


@router.get("", response_model=list[PlatformCategoryDTO])
async def list_platform_categories(
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> list[PlatformCategoryDTO]:
    return await bus.dispatch(ListPlatformCategories(user.id))


@admin_router.get("", response_model=list[PlatformCategoryDTO])
async def list_all_platform_categories(
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> list[PlatformCategoryDTO]:
    return await bus.dispatch(ListPlatformCategories(user.id, include_inactive=True))


@admin_router.post("", response_model=PlatformCategoryDTO, status_code=status.HTTP_201_CREATED)
async def create_platform_category(
    body: PlatformCategoryRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> PlatformCategoryDTO:
    return await bus.dispatch(CreatePlatformCategory(user.id, **body.model_dump()))


@admin_router.put("/{category_id}", response_model=PlatformCategoryDTO)
async def update_platform_category(
    category_id: uuid.UUID,
    body: PlatformCategoryRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> PlatformCategoryDTO:
    return await bus.dispatch(UpdatePlatformCategory(user.id, category_id, **body.model_dump()))


@admin_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_platform_category(
    category_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> Response:
    await bus.dispatch(DeletePlatformCategory(user.id, category_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
