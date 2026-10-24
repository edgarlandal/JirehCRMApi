from uuid import UUID

from fastapi import HTTPException

from app.models.appointment import Appointment
from app.models.user import User
from app.repositories.appointment import AppointmentRepository
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentUpdate,
)
from app.services.crm_base import CRMService, utc


class AppointmentService(CRMService[Appointment]):
    response_schema = AppointmentResponse

    def __init__(self, repo: AppointmentRepository):
        super().__init__(repo)

    @staticmethod
    def serialize_url(values: dict) -> dict:
        if values.get("meeting_url") is not None:
            values["meeting_url"] = str(values["meeting_url"])
        return values

    async def create(self, data: AppointmentCreate, actor: User) -> Appointment:
        values = self.serialize_url(data.model_dump())
        await self.validate_links(values, actor)
        return await self._create_record(Appointment(**values, created_by_id=actor.id))

    async def update(
        self, record_id: UUID, data: AppointmentUpdate, actor: User
    ) -> Appointment:
        record = await self.get_by_id(record_id, actor)
        values = self.serialize_url(data.model_dump(exclude_unset=True))
        starts_at = values.get("starts_at", record.starts_at)
        ends_at = values.get("ends_at", record.ends_at)
        if utc(ends_at) <= utc(starts_at):
            raise HTTPException(
                status_code=422, detail="ends_at must be after starts_at"
            )
        await self.validate_links(values, actor, record)
        return await self._update_record(record, values)
