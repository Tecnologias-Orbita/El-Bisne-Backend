import uuid
from dataclasses import dataclass

from sqlalchemy import select

from app.modules.businesses.application.services.authorization import (
    BusinessAuthorizationService,
    BusinessPermission,
)
from app.modules.businesses.infrastructure.repositories.sqlalchemy_businesses import (
    SqlAlchemyBusinessRepository,
)
from app.modules.forms.application.dto.forms import FormDTO, FormFieldInput, SubmissionDTO
from app.modules.forms.infrastructure.models.form import (
    FormFieldModel,
    FormModel,
    FormSubmissionModel,
)
from app.modules.notifications.infrastructure.models.notification import OutboxEventModel
from app.shared.application.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.domain.exceptions import NotFoundError, ValidationError

FIELD_TYPES = {"text", "textarea", "email", "phone", "number", "select", "checkbox"}


@dataclass(frozen=True)
class CreateForm:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    name: str
    description: str | None
    fields: list[FormFieldInput]


@dataclass(frozen=True)
class SubmitForm:
    business_slug: str
    form_id: uuid.UUID
    data: dict[str, object]
    contact_email: str | None = None
    contact_phone: str | None = None


class CreateFormHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: CreateForm) -> FormDTO:
        if any(field.field_type not in FIELD_TYPES for field in command.fields):
            raise ValidationError("Form contains an unsupported field type")
        async with self.uow:
            await BusinessAuthorizationService(self.uow.session).require(
                command.actor_user_id, command.business_id, BusinessPermission.MANAGE_CONTENT
            )
            form = FormModel(
                business_id=command.business_id,
                name=command.name.strip(),
                description=command.description,
                status="published",
            )
            self.uow.session.add(form)
            await self.uow.session.flush()
            for field in command.fields:
                self.uow.session.add(
                    FormFieldModel(
                        form_id=form.id,
                        name=field.name,
                        label=field.label,
                        field_type=field.field_type,
                        position=field.position,
                        is_required=field.is_required,
                        config=field.config or {},
                    )
                )
            await self.uow.commit()
            return FormDTO(form.id, form.name, form.status)


class SubmitFormHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: SubmitForm) -> SubmissionDTO:
        async with self.uow:
            business = await SqlAlchemyBusinessRepository(self.uow.session).get_by_slug(
                command.business_slug
            )
            if business is None or not business.is_published:
                raise NotFoundError("Business not found")
            form = await self.uow.session.scalar(
                select(FormModel).where(
                    FormModel.id == command.form_id,
                    FormModel.business_id == business.id,
                    FormModel.status == "published",
                )
            )
            if form is None:
                raise NotFoundError("Form not found")
            fields = list(
                await self.uow.session.scalars(
                    select(FormFieldModel).where(FormFieldModel.form_id == form.id)
                )
            )
            missing = [
                field.name
                for field in fields
                if field.is_required and not command.data.get(field.name)
            ]
            allowed = {field.name for field in fields}
            unknown = set(command.data) - allowed
            if missing:
                raise ValidationError(f"Missing required fields: {', '.join(missing)}")
            if unknown:
                raise ValidationError(f"Unknown fields: {', '.join(sorted(unknown))}")
            submission = FormSubmissionModel(
                form_id=form.id,
                business_id=business.id,
                data=command.data,
                contact_email=command.contact_email,
                contact_phone=command.contact_phone,
            )
            self.uow.session.add(submission)
            await self.uow.session.flush()
            self.uow.session.add(
                OutboxEventModel(
                    event_type="form.submitted",
                    payload={
                        "submission_id": str(submission.id),
                        "business_id": str(business.id),
                        "recipient": business.contact_email,
                    },
                )
            )
            await self.uow.commit()
            return SubmissionDTO(submission.id, submission.status)


@dataclass(frozen=True)
class UpdateForm:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    form_id: uuid.UUID
    name: str
    description: str | None
    status: str
    fields: list[FormFieldInput]


@dataclass(frozen=True)
class DeleteForm:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    form_id: uuid.UUID


@dataclass(frozen=True)
class UpdateSubmissionStatus:
    actor_user_id: uuid.UUID
    business_id: uuid.UUID
    submission_id: uuid.UUID
    status: str


class UpdateFormHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: UpdateForm) -> FormDTO:
        if command.status not in {"draft", "published", "archived"}:
            raise ValidationError("Invalid form status")
        if any(field.field_type not in FIELD_TYPES for field in command.fields):
            raise ValidationError("Form contains an unsupported field type")
        async with self.uow:
            await BusinessAuthorizationService(self.uow.session).require(
                command.actor_user_id, command.business_id, BusinessPermission.MANAGE_CONTENT
            )
            form = await self.uow.session.scalar(
                select(FormModel).where(
                    FormModel.id == command.form_id, FormModel.business_id == command.business_id
                )
            )
            if form is None:
                raise NotFoundError("Form not found")
            form.name = command.name.strip()
            form.description = command.description
            form.status = command.status
            for old_field in await self.uow.session.scalars(
                select(FormFieldModel).where(FormFieldModel.form_id == form.id)
            ):
                await self.uow.session.delete(old_field)
            await self.uow.session.flush()
            for field in command.fields:
                self.uow.session.add(
                    FormFieldModel(
                        form_id=form.id,
                        name=field.name,
                        label=field.label,
                        field_type=field.field_type,
                        position=field.position,
                        is_required=field.is_required,
                        config=field.config or {},
                    )
                )
            await self.uow.commit()
            return FormDTO(form.id, form.name, form.status)


class DeleteFormHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: DeleteForm) -> None:
        async with self.uow:
            await BusinessAuthorizationService(self.uow.session).require(
                command.actor_user_id, command.business_id, BusinessPermission.MANAGE_CONTENT
            )
            form = await self.uow.session.scalar(
                select(FormModel).where(
                    FormModel.id == command.form_id, FormModel.business_id == command.business_id
                )
            )
            if form is None:
                raise NotFoundError("Form not found")
            has_submissions = await self.uow.session.scalar(
                select(FormSubmissionModel.id)
                .where(FormSubmissionModel.form_id == form.id)
                .limit(1)
            )
            if has_submissions:
                form.status = "archived"
            else:
                await self.uow.session.delete(form)
            await self.uow.commit()


class UpdateSubmissionStatusHandler:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self.uow = uow

    async def __call__(self, command: UpdateSubmissionStatus) -> SubmissionDTO:
        if command.status not in {"new", "in_progress", "closed", "discarded"}:
            raise ValidationError("Invalid submission status")
        async with self.uow:
            await BusinessAuthorizationService(self.uow.session).require(
                command.actor_user_id, command.business_id, BusinessPermission.MANAGE_CONTENT
            )
            submission = await self.uow.session.scalar(
                select(FormSubmissionModel).where(
                    FormSubmissionModel.id == command.submission_id,
                    FormSubmissionModel.business_id == command.business_id,
                )
            )
            if submission is None:
                raise NotFoundError("Submission not found")
            submission.status = command.status
            await self.uow.commit()
            return SubmissionDTO(submission.id, submission.status)
