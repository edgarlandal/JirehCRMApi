from uuid import UUID

from app.models.contact import Contact
from app.models.user import User
from app.repositories.contact import ContactRepository
from app.schemas.contact import ContactCreate, ContactResponse, ContactUpdate
from app.services.crm_base import CRMService


class ContactService(CRMService[Contact]):
    response_schema = ContactResponse

    def __init__(self, repo: ContactRepository):
        super().__init__(repo)

    async def create(self, data: ContactCreate, actor: User) -> Contact:
        await self.validate_customer(data.customer_id, actor, creating=True)
        return await self._create_record(Contact(**data.model_dump()))

    async def update(
        self, record_id: UUID, data: ContactUpdate, actor: User
    ) -> Contact:
        record = await self.get_by_id(record_id, actor)
        return await self._update_record(record, data.model_dump(exclude_unset=True))

    async def deactivate(self, record_id: UUID, actor: User) -> Contact:
        return await self.update(record_id, ContactUpdate(is_active=False), actor)
