from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import Interaction
from app.repositories.crm_repository import CRMRepository


class InteractionRepository(CRMRepository[Interaction]):
    def __init__(self, db: AsyncSession):
        super().__init__(Interaction, db)
