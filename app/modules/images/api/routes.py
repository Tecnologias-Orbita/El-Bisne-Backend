import uuid
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.api.routes import get_current_user
from app.modules.auth.application.dto.auth import UserDTO
from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.modules.catalog.infrastructure.models.catalog import CategoryModel, ProductModel
from app.modules.images.infrastructure.storage import SupabaseImageStorage
from app.modules.services.infrastructure.models.service import ServiceModel
from app.modules.sites.infrastructure.models.site import BusinessSiteModel
from app.shared.domain.exceptions import NotFoundError, ValidationError

router = APIRouter(prefix="/businesses/{business_id}/images", tags=["images"])
MAX_IMAGE_SIZE = 500 * 1024
ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def has_valid_signature(content: bytes, content_type: str) -> bool:
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    return content.startswith(b"RIFF") and content[8:12] == b"WEBP"


class ImageKind(StrEnum):
    LOGO = "logo"
    HERO = "hero"
    PRODUCT = "product"
    SERVICE = "service"
    CATEGORY = "category"


class ImageResponse(BaseModel):
    url: str


async def target_for(
    session: AsyncSession, business_id: uuid.UUID, kind: ImageKind, resource_id: uuid.UUID | None
):
    if kind in {ImageKind.LOGO, ImageKind.HERO}:
        site = await session.scalar(
            select(BusinessSiteModel).where(BusinessSiteModel.business_id == business_id)
        )
        if site is None:
            site = BusinessSiteModel(business_id=business_id)
            session.add(site)
        return site, "logo_url" if kind == ImageKind.LOGO else "hero_image_url", kind.value
    if resource_id is None:
        raise ValidationError("resource_id is required for this image type")
    model, attribute, folder = {
        ImageKind.PRODUCT: (ProductModel, "image_url", "products"),
        ImageKind.SERVICE: (ServiceModel, "image_url", "services"),
        ImageKind.CATEGORY: (CategoryModel, "image_url", "categories"),
    }[kind]
    target = await session.get(model, resource_id)
    if target is None or target.business_id != business_id:
        raise NotFoundError("Image target not found")
    return target, attribute, f"{folder}/{resource_id}"


@router.post("/{kind}", response_model=ImageResponse)
async def upload_image(
    business_id: uuid.UUID,
    kind: ImageKind,
    user: Annotated[UserDTO, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    resource_id: uuid.UUID | None = None,
) -> ImageResponse:
    permission = (
        BusinessPermission.MANAGE_BUSINESS
        if kind in {ImageKind.LOGO, ImageKind.HERO}
        else BusinessPermission.MANAGE_CONTENT
    )
    await BusinessAuthorizationService(session).require(
        user.id, business_id, permission
    )
    extension = Path(file.filename or "").suffix.lower()
    if file.content_type not in ALLOWED_TYPES or extension not in ALLOWED_EXTENSIONS:
        raise ValidationError("Only JPEG, PNG and WebP images are allowed")
    content = await file.read(MAX_IMAGE_SIZE + 1)
    if not content or len(content) > MAX_IMAGE_SIZE:
        raise ValidationError("Image size must not exceed 500 KB")
    if not has_valid_signature(content, file.content_type):
        raise ValidationError("The file content is not a valid image")
    target, attribute, folder = await target_for(session, business_id, kind, resource_id)
    storage = SupabaseImageStorage()
    path = f"businesses/{business_id}/{folder}/{uuid.uuid4().hex}{ALLOWED_TYPES[file.content_type]}"
    url = await storage.upload(path, content, file.content_type)
    old_path = storage.path_from_public_url(getattr(target, attribute))
    setattr(target, attribute, url)
    try:
        await session.commit()
    except Exception:
        await storage.delete(path)
        raise
    if old_path:
        await storage.delete(old_path)
    return ImageResponse(url=url)


@router.delete("/{kind}")
async def delete_image(
    business_id: uuid.UUID,
    kind: ImageKind,
    user: Annotated[UserDTO, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    resource_id: uuid.UUID | None = None,
) -> None:
    permission = (
        BusinessPermission.MANAGE_BUSINESS
        if kind in {ImageKind.LOGO, ImageKind.HERO}
        else BusinessPermission.MANAGE_CONTENT
    )
    await BusinessAuthorizationService(session).require(
        user.id, business_id, permission
    )
    target, attribute, _ = await target_for(session, business_id, kind, resource_id)
    storage = SupabaseImageStorage()
    old_path = storage.path_from_public_url(getattr(target, attribute))
    if old_path:
        await storage.delete(old_path)
    setattr(target, attribute, None)
    await session.commit()
