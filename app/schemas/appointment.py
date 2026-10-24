from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field, HttpUrl, model_validator

from app.models.crm_enums import AppointmentStatus
from app.schemas.crm_base import (
    Content,
    CRMFilters,
    CRMInput,
    CRMPatch,
    CRMResponse,
    Name,
    UTCDateTime,
)


class AppointmentCreate(CRMInput):
    customer_id: UUID
    contact_id: UUID | None = None
    assigned_to_id: UUID
    title: Name
    description: Content | None = None
    starts_at: UTCDateTime
    ends_at: UTCDateTime
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    location: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    meeting_url: Annotated[HttpUrl, Field(max_length=2048)] | None = None

    @model_validator(mode="after")
    def validate_interval(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class AppointmentUpdate(CRMPatch):
    nonnullable = {"assigned_to_id", "title", "starts_at", "ends_at", "status"}
    contact_id: UUID | None = None
    assigned_to_id: UUID | None = None
    title: Name | None = None
    description: Content | None = None
    starts_at: UTCDateTime | None = None
    ends_at: UTCDateTime | None = None
    status: AppointmentStatus | None = None
    location: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    meeting_url: Annotated[HttpUrl, Field(max_length=2048)] | None = None


class AppointmentResponse(CRMResponse):
    customer_id: UUID
    contact_id: UUID | None
    assigned_to_id: UUID
    created_by_id: UUID
    title: Name
    description: Content | None
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    location: Annotated[str, Field(min_length=1, max_length=500)] | None
    meeting_url: str | None


class AppointmentFilters(CRMFilters):
    customer_id: UUID | None = None
    contact_id: UUID | None = None
    assigned_to_id: UUID | None = None
    status: AppointmentStatus | None = None
    starts_from: UTCDateTime | None = None
    starts_until: UTCDateTime | None = None
