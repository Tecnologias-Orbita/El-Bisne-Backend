import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.modules.forms.application.dto.forms import (
    FormDetailDTO,
    FormFieldInput,
    SubmissionDetailDTO,
)
from app.modules.forms.infrastructure.models.form import (
    FormFieldModel,
    FormModel,
    FormSubmissionModel,
)
from app.shared.domain.exceptions import NotFoundError


@dataclass(frozen=True)
class ListForms:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID


@dataclass(frozen=True)
class GetForm:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    form_id: uuid.UUID


@dataclass(frozen=True)
class ListSubmissions:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    form_id: uuid.UUID | None = None


async def _require_member(
    session: AsyncSession, business_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    await BusinessAuthorizationService(session).require(
        user_id, business_id, BusinessPermission.VIEW
    )


async def _form_dto(session: AsyncSession, form: FormModel) -> FormDetailDTO:
    fields = await session.scalars(
        select(FormFieldModel)
        .where(FormFieldModel.form_id == form.id)
        .order_by(FormFieldModel.position)
    )
    return FormDetailDTO(
        form.id,
        form.name,
        form.description,
        form.status,
        [
            FormFieldInput(x.name, x.label, x.field_type, x.position, x.is_required, x.config)
            for x in fields
        ],
    )


class ListFormsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: ListForms) -> list[FormDetailDTO]:
        await _require_member(self.session, query.business_id, query.actor_user_id)
        forms = await self.session.scalars(
            select(FormModel)
            .where(FormModel.business_id == query.business_id)
            .order_by(FormModel.name)
        )
        return [await _form_dto(self.session, form) for form in forms]


class GetFormHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: GetForm) -> FormDetailDTO:
        await _require_member(self.session, query.business_id, query.actor_user_id)
        form = await self.session.scalar(
            select(FormModel).where(
                FormModel.id == query.form_id, FormModel.business_id == query.business_id
            )
        )
        if form is None:
            raise NotFoundError("Form not found")
        return await _form_dto(self.session, form)


class ListSubmissionsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __call__(self, query: ListSubmissions) -> list[SubmissionDetailDTO]:
        await _require_member(self.session, query.business_id, query.actor_user_id)
        statement = select(FormSubmissionModel).where(
            FormSubmissionModel.business_id == query.business_id
        )
        if query.form_id:
            statement = statement.where(FormSubmissionModel.form_id == query.form_id)
        items = await self.session.scalars(
            statement.order_by(FormSubmissionModel.created_at.desc())
        )
        return [
            SubmissionDetailDTO(x.id, x.form_id, x.contact_email, x.contact_phone, x.data, x.status)
            for x in items
        ]
