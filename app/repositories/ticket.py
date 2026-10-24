from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket
from app.repositories.crm_repository import CRMRepository


class TicketRepository(CRMRepository[Ticket]):
    search_fields = ("subject",)

    def __init__(self, db: AsyncSession):
        super().__init__(Ticket, db)
