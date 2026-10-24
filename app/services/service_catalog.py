from uuid import UUID

from app.models.service import Service
from app.models.user import User
from app.repositories.service import ServiceRepository
from app.schemas.service import ServiceCreate, ServiceResponse, ServiceUpdate
from app.services.crm_base import CRMService


class ServiceCatalogService(CRMService[Service]):
    response_schema = ServiceResponse
    catalog = True

    def __init__(self, repo: ServiceRepository):
        super().__init__(repo)

    async def create(self, data: ServiceCreate, actor: User) -> Service:
        self.require_admin(actor)
        return await self._create_record(Service(**data.model_dump()))

    async def update(
        self, record_id: UUID, data: ServiceUpdate, actor: User
    ) -> Service:
        self.require_admin(actor)
        record = await self.get_by_id(record_id, actor)
        return await self._update_record(record, data.model_dump(exclude_unset=True))

    async def deactivate(self, record_id: UUID, actor: User) -> Service:
        return await self.update(record_id, ServiceUpdate(is_active=False), actor)
