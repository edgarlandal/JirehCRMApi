from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import Service
from app.repositories.crm_repository import CRMRepository


class ServiceRepository(CRMRepository[Service]):
    search_fields = (
        "name",
        "category",
    )

    def __init__(self, db: AsyncSession):
        super().__init__(Service, db)

    async def deactivate(self, record: Service) -> Service:
        return await self.update(record, {"is_active": False})
