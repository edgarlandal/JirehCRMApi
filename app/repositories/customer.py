from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.repositories.crm_repository import CRMRepository


class CustomerRepository(CRMRepository[Customer]):
    search_fields = (
        "name",
        "tax_id",
    )

    def __init__(self, db: AsyncSession):
        super().__init__(Customer, db)

    async def archive(self, record: Customer) -> Customer:
        from app.models.crm_enums import CustomerStatus

        return await self.update(record, {"status": CustomerStatus.INACTIVE})
