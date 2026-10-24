from uuid import UUID

from fastapi import HTTPException

from app.models.crm_base import utcnow
from app.models.crm_enums import TicketStatus
from app.models.ticket import Ticket
from app.models.user import User
from app.repositories.ticket import TicketRepository
from app.schemas.ticket import TicketCreate, TicketResponse, TicketUpdate
from app.services.crm_base import CRMService

TICKET_TRANSITIONS = {
    TicketStatus.OPEN: {
        TicketStatus.IN_PROGRESS,
        TicketStatus.WAITING_CUSTOMER,
        TicketStatus.RESOLVED,
    },
    TicketStatus.IN_PROGRESS: {TicketStatus.WAITING_CUSTOMER, TicketStatus.RESOLVED},
    TicketStatus.WAITING_CUSTOMER: {TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED},
    TicketStatus.RESOLVED: {TicketStatus.CLOSED, TicketStatus.OPEN},
    TicketStatus.CLOSED: {TicketStatus.OPEN},
}


class TicketService(CRMService[Ticket]):
    response_schema = TicketResponse

    def __init__(self, repo: TicketRepository):
        super().__init__(repo)

    async def create(self, data: TicketCreate, actor: User) -> Ticket:
        values = data.model_dump()
        await self.validate_links(values, actor)
        return await self._create_record(Ticket(**values, created_by_id=actor.id))

    async def update(self, record_id: UUID, data: TicketUpdate, actor: User) -> Ticket:
        record = await self.get_by_id(record_id, actor)
        values = data.model_dump(exclude_unset=True)
        await self.validate_links(values, actor, record)
        target = values.get("status", record.status)
        if target != record.status:
            if target not in TICKET_TRANSITIONS[record.status]:
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot transition from {record.status.value} to {target.value}",
                )
            if target == TicketStatus.RESOLVED:
                values.update(resolved_at=utcnow(), closed_at=None)
            elif target == TicketStatus.CLOSED:
                values["closed_at"] = utcnow()
            else:
                values.update(resolved_at=None, closed_at=None)
        return await self._update_record(record, values)
