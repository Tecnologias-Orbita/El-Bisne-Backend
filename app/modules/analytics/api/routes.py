import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field

from app.modules.analytics.application.commands.analytics import TrackPublicEvent
from app.modules.analytics.application.dto.analytics import DashboardDTO
from app.modules.analytics.application.queries.analytics import GetBusinessDashboard
from app.modules.auth.api.routes import get_current_user
from app.modules.auth.application.dto.auth import UserDTO
from app.shared.application.cqrs import CommandBus, QueryBus
from app.shared.infrastructure.dependencies import get_command_bus, get_query_bus

router = APIRouter(tags=["analytics"])


class TrackEventRequest(BaseModel):
    event_type: str
    resource_id: uuid.UUID | None = None
    anonymous_reference: str | None = Field(default=None, max_length=64)


@router.post("/public/businesses/{business_slug}/events", status_code=status.HTTP_204_NO_CONTENT)
async def track_event(
    business_slug: str,
    body: TrackEventRequest,
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> Response:
    await bus.dispatch(TrackPublicEvent(business_slug, **body.model_dump()))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/businesses/{business_id}/analytics", response_model=DashboardDTO)
async def business_dashboard(
    business_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> DashboardDTO:
    return await bus.dispatch(GetBusinessDashboard(user.id, business_id))
