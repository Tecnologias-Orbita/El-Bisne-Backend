import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, EmailStr, Field

from app.modules.auth.api.routes import get_current_user
from app.modules.auth.application.dto.auth import UserDTO
from app.modules.forms.application.commands.forms import (
    CreateForm,
    DeleteForm,
    SubmitForm,
    UpdateForm,
    UpdateSubmissionStatus,
)
from app.modules.forms.application.dto.forms import (
    FormDetailDTO,
    FormDTO,
    FormFieldInput,
    SubmissionDetailDTO,
    SubmissionDTO,
)
from app.modules.forms.application.queries.forms import GetForm, ListForms, ListSubmissions
from app.shared.application.cqrs import CommandBus, QueryBus
from app.shared.infrastructure.dependencies import get_command_bus, get_query_bus

admin_router = APIRouter(prefix="/businesses/{business_id}/forms", tags=["forms"])
public_router = APIRouter(prefix="/public/businesses", tags=["public-forms"])


class FormFieldRequest(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=80)
    label: str = Field(min_length=1, max_length=160)
    field_type: str
    position: int = Field(ge=0)
    is_required: bool = False
    config: dict[str, object] = Field(default_factory=dict)


class CreateFormRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    fields: list[FormFieldRequest] = Field(min_length=1, max_length=100)


class SubmitFormRequest(BaseModel):
    data: dict[str, object]
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=32)


class UpdateFormRequest(CreateFormRequest):
    status: str


class SubmissionStatusRequest(BaseModel):
    status: str


@admin_router.post("", response_model=FormDTO, status_code=status.HTTP_201_CREATED)
async def create_form(
    business_id: uuid.UUID,
    body: CreateFormRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> FormDTO:
    return await bus.dispatch(
        CreateForm(
            actor_user_id=user.id,
            business_id=business_id,
            name=body.name,
            description=body.description,
            fields=[FormFieldInput(**field.model_dump()) for field in body.fields],
        )
    )


@admin_router.get("", response_model=list[FormDetailDTO])
async def list_forms(
    business_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> list[FormDetailDTO]:
    return await bus.dispatch(ListForms(user.id, business_id))


@admin_router.get("/{form_id}", response_model=FormDetailDTO)
async def get_form(
    business_id: uuid.UUID,
    form_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
) -> FormDetailDTO:
    return await bus.dispatch(GetForm(user.id, business_id, form_id))


@admin_router.put("/{form_id}", response_model=FormDTO)
async def update_form(
    business_id: uuid.UUID,
    form_id: uuid.UUID,
    body: UpdateFormRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> FormDTO:
    return await bus.dispatch(
        UpdateForm(
            user.id,
            business_id,
            form_id,
            body.name,
            body.description,
            body.status,
            [FormFieldInput(**field.model_dump()) for field in body.fields],
        )
    )


@admin_router.delete("/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_form(
    business_id: uuid.UUID,
    form_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> Response:
    await bus.dispatch(DeleteForm(user.id, business_id, form_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.get("/management/submissions", response_model=list[SubmissionDetailDTO])
async def list_submissions(
    business_id: uuid.UUID,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[QueryBus, Depends(get_query_bus)],
    form_id: uuid.UUID | None = None,
) -> list[SubmissionDetailDTO]:
    return await bus.dispatch(ListSubmissions(user.id, business_id, form_id))


@admin_router.patch("/management/submissions/{submission_id}", response_model=SubmissionDTO)
async def update_submission_status(
    business_id: uuid.UUID,
    submission_id: uuid.UUID,
    body: SubmissionStatusRequest,
    user: Annotated[UserDTO, Depends(get_current_user)],
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> SubmissionDTO:
    return await bus.dispatch(
        UpdateSubmissionStatus(user.id, business_id, submission_id, body.status)
    )


@public_router.post(
    "/{business_slug}/forms/{form_id}/submissions",
    response_model=SubmissionDTO,
    status_code=status.HTTP_201_CREATED,
)
async def submit_form(
    business_slug: str,
    form_id: uuid.UUID,
    body: SubmitFormRequest,
    bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> SubmissionDTO:
    return await bus.dispatch(
        SubmitForm(
            business_slug,
            form_id,
            body.data,
            str(body.contact_email) if body.contact_email else None,
            body.contact_phone,
        )
    )
