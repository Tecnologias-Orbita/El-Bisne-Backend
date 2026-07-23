import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class FormFieldInput:
    name: str
    label: str
    field_type: str
    position: int
    is_required: bool = False
    config: dict[str, object] | None = None


@dataclass(frozen=True)
class FormDTO:
    id: uuid.UUID
    name: str
    status: str


@dataclass(frozen=True)
class SubmissionDTO:
    id: uuid.UUID
    status: str


@dataclass(frozen=True)
class FormDetailDTO:
    id: uuid.UUID
    name: str
    description: str | None
    status: str
    fields: list[FormFieldInput]


@dataclass(frozen=True)
class SubmissionDetailDTO:
    id: uuid.UUID
    form_id: uuid.UUID
    contact_email: str | None
    contact_phone: str | None
    data: dict[str, object]
    status: str
