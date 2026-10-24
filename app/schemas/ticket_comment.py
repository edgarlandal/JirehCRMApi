from uuid import UUID

from app.schemas.crm_base import Content, CRMFilters, CRMInput, CRMPatch, CRMResponse


class TicketCommentCreate(CRMInput):
    ticket_id: UUID
    body: Content
    is_internal: bool = True


class TicketCommentUpdate(CRMPatch):
    nonnullable = {"body", "is_internal"}
    body: Content | None = None
    is_internal: bool | None = None


class TicketCommentResponse(CRMResponse):
    ticket_id: UUID
    author_user_id: UUID
    body: Content
    is_internal: bool


class TicketCommentFilters(CRMFilters):
    ticket_id: UUID | None = None
