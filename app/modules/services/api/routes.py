import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.modules.auth.api.routes import get_current_user
from app.modules.auth.application.dto.auth import UserDTO
from app.modules.services.application.commands.services import (
    ArchiveService,
    CreateService,
    UpdateService,
)
from app.modules.services.application.dto.services import ServiceDTO
from app.modules.services.application.queries.services import (
    GetService,
    ListPublicServices,
    ListServices,
)
from app.shared.application.cqrs import CommandBus, QueryBus
from app.shared.infrastructure.dependencies import get_command_bus, get_query_bus

admin_router = APIRouter(prefix="/businesses/{business_id}/services", tags=["services"])
public_router = APIRouter(prefix="/public/businesses", tags=["public"])


class ServiceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=3, max_length=120)
    category_id: uuid.UUID | None = None
    platform_category_id: uuid.UUID | None = None
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    duration_minutes: int | None = Field(default=None, ge=1)
    image_url: HttpUrl | None = None
    is_published: bool = False
    is_available: bool = True

    @model_validator(mode="after")
    def price_requires_currency(self) -> "ServiceRequest":
        if (self.price is None) != (self.currency is None):
            raise ValueError("price and currency must be provided together")
        return self


class UpdateServiceRequest(ServiceRequest):
    pass


def payload(body: ServiceRequest) -> dict[str, object]:
    data = body.model_dump(mode="json")
    data.update(
        price=body.price,
        category_id=body.category_id,
        platform_category_id=body.platform_category_id,
    )
    return data


@admin_router.post("", response_model=ServiceDTO, status_code=status.HTTP_201_CREATED)
async def create_service(
    business_id: uuid.UUID,
    body: ServiceRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> ServiceDTO:
    return await bus.dispatch(
        CreateService(actor_user_id=user.id, business_id=business_id, **payload(body))
    )


@admin_router.get("", response_model=list[ServiceDTO])
async def list_services(
    business_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> list[ServiceDTO]:
    return await bus.dispatch(ListServices(user.id, business_id))


@admin_router.get("/{service_id}", response_model=ServiceDTO)
async def get_service(
    business_id: uuid.UUID,
    service_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> ServiceDTO:
    return await bus.dispatch(GetService(user.id, business_id, service_id))


@admin_router.put("/{service_id}", response_model=ServiceDTO)
async def update_service(
    business_id: uuid.UUID,
    service_id: uuid.UUID,
    body: UpdateServiceRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> ServiceDTO:
    return await bus.dispatch(
        UpdateService(
            actor_user_id=user.id, business_id=business_id, service_id=service_id, **payload(body)
        )
    )


@admin_router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_service(
    business_id: uuid.UUID,
    service_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> Response:
    await bus.dispatch(ArchiveService(user.id, business_id, service_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@public_router.get("/{business_slug}/services", response_model=list[ServiceDTO])
async def list_public_services(
    business_slug: str, bus: Annotated[QueryBus, Depends(get_query_bus)]
) -> list[ServiceDTO]:
    return await bus.dispatch(ListPublicServices(business_slug))
