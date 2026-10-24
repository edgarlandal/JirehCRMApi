from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.repositories.crm_repository import CRMRepository


class AppointmentRepository(CRMRepository[Appointment]):
    def __init__(self, db: AsyncSession):
        super().__init__(Appointment, db)
