from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket_comment import TicketComment
from app.repositories.crm_repository import CRMRepository


class TicketCommentRepository(CRMRepository[TicketComment]):
    def __init__(self, db: AsyncSession):
        super().__init__(TicketComment, db)
