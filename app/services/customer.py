from uuid import UUID

from app.models.crm_enums import CustomerStatus
from app.models.customer import Customer
from app.models.user import User, UserRole
from app.repositories.customer import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.services.crm_base import CRMService


class CustomerService(CRMService[Customer]):
    response_schema = CustomerResponse

    def __init__(self, repo: CustomerRepository):
        super().__init__(repo)

    async def create(self, data: CustomerCreate, actor: User) -> Customer:
        self.scope(actor)
        values = data.model_dump()
        if actor.role == UserRole.USER:
            values["assigned_to_id"] = actor.id
        await self.validate_assignee(values["assigned_to_id"])
        return await self._create_record(Customer(**values, created_by_id=actor.id))

    async def update(
        self, record_id: UUID, data: CustomerUpdate, actor: User
    ) -> Customer:
        record = await self.get_by_id(record_id, actor)
        values = data.model_dump(exclude_unset=True)
        if "assigned_to_id" in values:
            self.require_admin(actor)
            await self.validate_assignee(values["assigned_to_id"])
        return await self._update_record(record, values)

    async def archive(self, record_id: UUID, actor: User) -> Customer:
        return await self.update(
            record_id, CustomerUpdate(status=CustomerStatus.INACTIVE), actor
        )
