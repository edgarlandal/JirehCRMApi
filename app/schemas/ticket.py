from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.models.crm_enums import TicketPriority, TicketStatus
from app.schemas.crm_base import (
    Content,
    CRMFilters,
    CRMInput,
    CRMPatch,
    CRMResponse,
    Name,
)


class TicketCreate(CRMInput):
    customer_id: UUID
    contact_id: UUID | None = None
    service_id: UUID | None = None
    assigned_to_id: UUID | None = None
    subject: Name
    description: Content
    priority: TicketPriority = TicketPriority.NORMAL


class TicketUpdate(CRMPatch):
    nonnullable = {"subject", "description", "status", "priority"}
    contact_id: UUID | None = None
    service_id: UUID | None = None
    assigned_to_id: UUID | None = None
    subject: Name | None = None
    description: Content | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | None = None


class TicketResponse(CRMResponse):
    customer_id: UUID
    contact_id: UUID | None
    service_id: UUID | None
    assigned_to_id: UUID | None
    created_by_id: UUID
    subject: Name
    description: Content
    status: TicketStatus
    priority: TicketPriority
    resolved_at: datetime | None
    closed_at: datetime | None


class TicketFilters(CRMFilters):
    customer_id: UUID | None = None
    contact_id: UUID | None = None
    service_id: UUID | None = None
    assigned_to_id: UUID | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    search: Annotated[str, Field(min_length=1, max_length=255)] | None = None
