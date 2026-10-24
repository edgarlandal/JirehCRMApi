from uuid import UUID

from app.models.interaction import Interaction
from app.models.user import User
from app.repositories.interaction import InteractionRepository
from app.schemas.interaction import (
    InteractionCreate,
    InteractionResponse,
    InteractionUpdate,
)
from app.services.crm_base import CRMService


class InteractionService(CRMService[Interaction]):
    response_schema = InteractionResponse

    def __init__(self, repo: InteractionRepository):
        super().__init__(repo)

    async def create(self, data: InteractionCreate, actor: User) -> Interaction:
        values = data.model_dump()
        await self.validate_links(values, actor)
        return await self._create_record(Interaction(**values, created_by_id=actor.id))

    async def update(
        self, record_id: UUID, data: InteractionUpdate, actor: User
    ) -> Interaction:
        record = await self.get_by_id(record_id, actor)
        values = data.model_dump(exclude_unset=True)
        await self.validate_links(values, actor, record)
        return await self._update_record(record, values)
