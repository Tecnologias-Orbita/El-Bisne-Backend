import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.modules.businesses.application.dto.business import BusinessDTO
from app.modules.sites.application.queries.sites import (
    DiscoverPlatform,
    GetPublicBusiness,
    PlatformDiscoveryDTO,
)
from app.shared.application.cqrs import QueryBus
from app.shared.infrastructure.dependencies import get_query_bus

public_router = APIRouter(prefix="/public/businesses", tags=["public"])


@public_router.get("/discovery", response_model=PlatformDiscoveryDTO)
async def discover_platform(
    bus: Annotated[QueryBus, Depends(get_query_bus)],
    search: str | None = Query(default=None, max_length=160),
    platform_category_id: uuid.UUID | None = None,
) -> PlatformDiscoveryDTO:
    return await bus.dispatch(DiscoverPlatform(search, platform_category_id))


@public_router.get("/{business_slug}", response_model=BusinessDTO)
async def get_public_business(
    business_slug: str,
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> BusinessDTO:
    return await bus.dispatch(GetPublicBusiness(business_slug))
