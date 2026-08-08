import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from pydantic import BaseModel

from app.modules.auth.api.routes import get_current_user
from app.modules.auth.application.dto.auth import UserDTO
from app.modules.images.application.commands import DeleteImage, UploadImage
from app.shared.application.cqrs import CommandBus
from app.shared.infrastructure.dependencies import get_command_bus

router = APIRouter(prefix="/businesses/{business_id}/images", tags=["images"])


class ImageResponse(BaseModel):
    url: str


@router.post("/{kind}", response_model=ImageResponse)
async def upload_image(
    business_id: uuid.UUID,
    kind: str,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
    file: Annotated[UploadFile, File()],
    resource_id: uuid.UUID | None = None,
) -> ImageResponse:
    content = await file.read(500 * 1024 + 1)
    url = await bus.dispatch(
        UploadImage(
            user.id,
            business_id,
            kind,
            resource_id,
            file.filename or "",
            file.content_type or "",
            content,
        )
    )
    return ImageResponse(url=url)


@router.delete("/{kind}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    business_id: uuid.UUID,
    kind: str,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
    resource_id: uuid.UUID | None = None,
) -> Response:
    await bus.dispatch(DeleteImage(user.id, business_id, kind, resource_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
