from uuid import UUID

from app.models.ticket_comment import TicketComment
from app.models.user import User
from app.repositories.ticket import TicketRepository
from app.repositories.ticket_comment import TicketCommentRepository
from app.schemas.ticket_comment import (
    TicketCommentCreate,
    TicketCommentFilters,
    TicketCommentResponse,
    TicketCommentUpdate,
)
from app.services.crm_base import CRMService
from app.services.ticket import TicketService


class TicketCommentService(CRMService[TicketComment]):
    response_schema = TicketCommentResponse

    def __init__(self, repo: TicketCommentRepository):
        super().__init__(repo)
        self.tickets = TicketService(TicketRepository(repo.db))

    async def get_by_id(self, record_id: UUID, actor: User) -> TicketComment:
        # The scoped join checks ticket/customer access before returning the comment.
        return await super().get_by_id(record_id, actor)

    async def get_all(self, filters: TicketCommentFilters, actor: User):
        if filters.ticket_id is not None:
            await self.tickets.get_by_id(filters.ticket_id, actor)
        return await super().get_all(filters, actor)

    async def create(self, data: TicketCommentCreate, actor: User) -> TicketComment:
        await self.tickets.get_by_id(data.ticket_id, actor)
        return await self._create_record(
            TicketComment(**data.model_dump(), author_user_id=actor.id)
        )

    async def update(
        self, record_id: UUID, data: TicketCommentUpdate, actor: User
    ) -> TicketComment:
        record = await self.get_by_id(record_id, actor)
        return await self._update_record(record, data.model_dump(exclude_unset=True))
