from datetime import datetime
from uuid import UUID

from app.models.crm_enums import InteractionChannel
from app.schemas.crm_base import (
    Content,
    CRMFilters,
    CRMInput,
    CRMPatch,
    CRMResponse,
    UTCDateTime,
)


class InteractionCreate(CRMInput):
    customer_id: UUID
    contact_id: UUID | None = None
    channel: InteractionChannel
    summary: Content
    occurred_at: UTCDateTime


class InteractionUpdate(CRMPatch):
    nonnullable = {"channel", "summary", "occurred_at"}
    contact_id: UUID | None = None
    channel: InteractionChannel | None = None
    summary: Content | None = None
    occurred_at: UTCDateTime | None = None


class InteractionResponse(CRMResponse):
    customer_id: UUID
    contact_id: UUID | None
    created_by_id: UUID
    channel: InteractionChannel
    summary: Content
    occurred_at: datetime


class InteractionFilters(CRMFilters):
    customer_id: UUID | None = None
    contact_id: UUID | None = None
    channel: InteractionChannel | None = None
    occurred_from: UTCDateTime | None = None
    occurred_until: UTCDateTime | None = None
