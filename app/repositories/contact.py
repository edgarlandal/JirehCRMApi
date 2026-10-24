from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.repositories.crm_repository import CRMRepository


class ContactRepository(CRMRepository[Contact]):
    search_fields = (
        "firstname",
        "lastname",
        "email",
    )

    def __init__(self, db: AsyncSession):
        super().__init__(Contact, db)

    async def deactivate(self, record: Contact) -> Contact:
        return await self.update(record, {"is_active": False})
