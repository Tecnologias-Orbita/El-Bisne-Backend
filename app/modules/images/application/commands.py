import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.modules.catalog.infrastructure.models.catalog import CategoryModel, ProductModel
from app.modules.images.infrastructure.storage import SupabaseImageStorage
from app.modules.services.infrastructure.models.service import ServiceModel
from app.modules.sites.infrastructure.models.site import BusinessSiteModel
from app.shared.application.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.domain.exceptions import NotFoundError, ValidationError

MAX_IMAGE_SIZE = 500 * 1024
ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
IMAGE_KINDS = {"logo", "hero", "product", "service", "category"}


def has_valid_signature(content: bytes, content_type: str) -> bool:
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    return content.startswith(b"RIFF") and content[8:12] == b"WEBP"


@dataclass(frozen=True)
class UploadImage:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    kind: str
    resource_id: uuid.UUID | None
    filename: str
    content_type: str
    content: bytes


@dataclass(frozen=True)
class DeleteImage:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    kind: str
    resource_id: uuid.UUID | None


async def _target(
    session: AsyncSession, business_id: uuid.UUID, kind: str, resource_id: uuid.UUID | None
):
    if kind in {"logo", "hero"}:
        site = await session.scalar(
            select(BusinessSiteModel).where(BusinessSiteModel.business_id == business_id)
        )
        if site is None:
            site = BusinessSiteModel(business_id=business_id)
            session.add(site)
        return site, "logo_url" if kind == "logo" else "hero_image_url", kind
    if resource_id is None:
        raise ValidationError("resource_id is required for this image type")
    model, attribute, folder = {
        "product": (ProductModel, "image_url", "products"),
        "service": (ServiceModel, "image_url", "services"),
        "category": (CategoryModel, "image_url", "categories"),
    }[kind]
    target = await session.get(model, resource_id)
    if target is None or target.business_id != business_id:
        raise NotFoundError("Image target not found")
    return target, attribute, f"{folder}/{resource_id}"


async def _authorize(session: AsyncSession, actor: uuid.UUID, business: uuid.UUID, kind: str):
    permission = (
        BusinessPermission.MANAGE_BUSINESS
        if kind in {"logo", "hero"}
        else BusinessPermission.MANAGE_CONTENT
    )
    await BusinessAuthorizationService(session).require(actor, business, permission)


class UploadImageHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: UploadImage) -> str:
        if command.kind not in IMAGE_KINDS:
            raise ValidationError("Invalid image type")
        extension = Path(command.filename).suffix.lower()
        if command.content_type not in ALLOWED_TYPES or extension not in ALLOWED_EXTENSIONS:
            raise ValidationError("Only JPEG, PNG and WebP images are allowed")
        if not command.content or len(command.content) > MAX_IMAGE_SIZE:
            raise ValidationError("Image size must not exceed 500 KB")
        if not has_valid_signature(command.content, command.content_type):
            raise ValidationError("The file content is not a valid image")
        async with self.uow:
            await _authorize(
                self.uow.session, command.actor_user_id, command.business_id, command.kind
            )
            target, attribute, folder = await _target(
                self.uow.session, command.business_id, command.kind, command.resource_id
            )
            storage = SupabaseImageStorage()
            path = (
                f"businesses/{command.business_id}/{folder}/"
                f"{uuid.uuid4().hex}{ALLOWED_TYPES[command.content_type]}"
            )
            url = await storage.upload(path, command.content, command.content_type)
            old_path = storage.path_from_public_url(getattr(target, attribute))
            setattr(target, attribute, url)
            try:
                await self.uow.commit()
            except Exception:
                await storage.delete(path)
                raise
            if old_path:
                await storage.delete(old_path)
            return url


class DeleteImageHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: DeleteImage) -> None:
        if command.kind not in IMAGE_KINDS:
            raise ValidationError("Invalid image type")
        async with self.uow:
            await _authorize(
                self.uow.session, command.actor_user_id, command.business_id, command.kind
            )
            target, attribute, _ = await _target(
                self.uow.session, command.business_id, command.kind, command.resource_id
            )
            storage = SupabaseImageStorage()
            old_path = storage.path_from_public_url(getattr(target, attribute))
            if old_path:
                await storage.delete(old_path)
            setattr(target, attribute, None)
            await self.uow.commit()
