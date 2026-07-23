import uuid
from dataclasses import dataclass

from sqlalchemy import select

from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.modules.businesses.infrastructure.models.business import BusinessModel
from app.modules.sites.application.dto.sites import SectionDTO
from app.modules.sites.infrastructure.models.site import (
    BusinessSiteModel,
    SiteSectionModel,
)
from app.shared.application.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.domain.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

SECTION_TYPES = {"hero", "text", "gallery", "contact", "form"}


@dataclass(frozen=True)
class AddSiteSection:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    section_type: str
    position: int
    content: dict[str, object]


@dataclass(frozen=True)
class PublishSite:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    publish: bool = True


class AddSiteSectionHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: AddSiteSection) -> SectionDTO:
        if command.section_type not in SECTION_TYPES:
            raise ValidationError("Unsupported site section type")
        async with self.uow:
            await BusinessAuthorizationService(self.uow.session).require(
                command.actor_user_id, command.business_id, BusinessPermission.MANAGE_CONTENT
            )
            site = await self.uow.session.scalar(
                select(BusinessSiteModel).where(
                    BusinessSiteModel.business_id == command.business_id
                )
            )
            if site is None:
                raise NotFoundError("Business site not found")
            duplicate = await self.uow.session.scalar(
                select(SiteSectionModel.id).where(
                    SiteSectionModel.site_id == site.id,
                    SiteSectionModel.position == command.position,
                )
            )
            if duplicate:
                raise ConflictError("A section already uses this position")
            section = SiteSectionModel(
                site_id=site.id,
                section_type=command.section_type,
                position=command.position,
                content=command.content,
            )
            self.uow.session.add(section)
            await self.uow.session.flush()
            await self.uow.commit()
            return SectionDTO(
                section.id,
                section.section_type,
                section.position,
                section.content,
                section.is_visible,
            )


class PublishSiteHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: PublishSite) -> None:
        async with self.uow:
            await BusinessAuthorizationService(self.uow.session).require(
                command.actor_user_id, command.business_id, BusinessPermission.MANAGE_CONTENT
            )
            site = await self.uow.session.scalar(
                select(BusinessSiteModel).where(
                    BusinessSiteModel.business_id == command.business_id
                )
            )
            business = await self.uow.session.get(BusinessModel, command.business_id)
            if site is None or business is None:
                raise NotFoundError("Business site not found")
            site.is_published = command.publish
            business.is_published = command.publish
            await self.uow.commit()


@dataclass(frozen=True)
class UpdateSiteSettings:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    favicon_url: str | None
    palette: dict[str, object]
    typography: dict[str, object]
    seo: dict[str, object]


@dataclass(frozen=True)
class UpdateSiteSection:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    section_id: uuid.UUID
    section_type: str
    position: int
    content: dict[str, object]
    is_visible: bool


@dataclass(frozen=True)
class DeleteSiteSection:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    section_id: uuid.UUID


async def _get_managed_site(
    uow: SqlAlchemyUnitOfWork, business_id: uuid.UUID, user_id: uuid.UUID
) -> BusinessSiteModel:
    await BusinessAuthorizationService(uow.session).require(
        user_id, business_id, BusinessPermission.MANAGE_CONTENT
    )
    site = await uow.session.scalar(
        select(BusinessSiteModel).where(BusinessSiteModel.business_id == business_id)
    )
    if site is None:
        raise NotFoundError("Business site not found")
    return site


class UpdateSiteSettingsHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: UpdateSiteSettings) -> None:
        async with self.uow:
            site = await _get_managed_site(self.uow, command.business_id, command.actor_user_id)
            site.favicon_url = command.favicon_url
            site.palette = command.palette
            site.typography = command.typography
            site.seo = command.seo
            await self.uow.commit()


class UpdateSiteSectionHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: UpdateSiteSection) -> SectionDTO:
        if command.section_type not in SECTION_TYPES:
            raise ValidationError("Unsupported site section type")
        async with self.uow:
            site = await _get_managed_site(self.uow, command.business_id, command.actor_user_id)
            section = await self.uow.session.scalar(
                select(SiteSectionModel).where(
                    SiteSectionModel.id == command.section_id, SiteSectionModel.site_id == site.id
                )
            )
            if section is None:
                raise NotFoundError("Site section not found")
            duplicate = await self.uow.session.scalar(
                select(SiteSectionModel.id).where(
                    SiteSectionModel.site_id == site.id,
                    SiteSectionModel.position == command.position,
                    SiteSectionModel.id != section.id,
                )
            )
            if duplicate:
                raise ConflictError("A section already uses this position")
            section.section_type = command.section_type
            section.position = command.position
            section.content = command.content
            section.is_visible = command.is_visible
            await self.uow.commit()
            return SectionDTO(
                section.id,
                section.section_type,
                section.position,
                section.content,
                section.is_visible,
            )


class DeleteSiteSectionHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: DeleteSiteSection) -> None:
        async with self.uow:
            site = await _get_managed_site(self.uow, command.business_id, command.actor_user_id)
            section = await self.uow.session.scalar(
                select(SiteSectionModel).where(
                    SiteSectionModel.id == command.section_id, SiteSectionModel.site_id == site.id
                )
            )
            if section is None:
                raise NotFoundError("Site section not found")
            await self.uow.session.delete(section)
            await self.uow.commit()
