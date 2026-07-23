import uuid
from dataclasses import dataclass

from app.modules.analytics.infrastructure.models.analytics import AnalyticsEventModel
from app.modules.businesses.infrastructure.repositories.sqlalchemy_businesses import (
    SqlAlchemyBusinessRepository,
)
from app.shared.application.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.domain.exceptions import NotFoundError, ValidationError

PUBLIC_EVENTS = {"site_view", "product_view"}


@dataclass(frozen=True)
class TrackPublicEvent:
    business_slug: str
    event_type: str
    resource_id: uuid.UUID | None
    anonymous_reference: str | None


class TrackPublicEventHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: TrackPublicEvent) -> None:
        if command.event_type not in PUBLIC_EVENTS:
            raise ValidationError("Unsupported analytics event")
        async with self.uow:
            business = await SqlAlchemyBusinessRepository(self.uow.session).get_by_slug(
                command.business_slug
            )
            if business is None or not business.is_published:
                raise NotFoundError("Business not found")
            self.uow.session.add(
                AnalyticsEventModel(
                    business_id=business.id,
                    event_type=command.event_type,
                    resource_type="product" if command.event_type == "product_view" else "site",
                    resource_id=command.resource_id,
                    anonymous_reference=command.anonymous_reference,
                )
            )
            await self.uow.commit()
