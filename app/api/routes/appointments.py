from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import ActiveUser, get_appointment_service
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentFilters,
    AppointmentResponse,
    AppointmentUpdate,
)
from app.schemas.pagination import PaginateResponse
from app.services.appointment import AppointmentService

router = APIRouter(prefix="/appointments", tags=["Appointment"])
AppointmentDependency = Annotated[AppointmentService, Depends(get_appointment_service)]


@router.post(
    "", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED
)
async def create_appointment(
    data: AppointmentCreate,
    actor: ActiveUser,
    service: AppointmentDependency,
):
    return await service.create(data, actor)


@router.get("", response_model=PaginateResponse[AppointmentResponse])
async def list_appointments(
    filters: Annotated[AppointmentFilters, Query()],
    actor: ActiveUser,
    service: AppointmentDependency,
):
    return await service.get_all(filters, actor)


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: UUID,
    actor: ActiveUser,
    service: AppointmentDependency,
):
    return await service.get_by_id(appointment_id, actor)


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: UUID,
    data: AppointmentUpdate,
    actor: ActiveUser,
    service: AppointmentDependency,
):
    return await service.update(appointment_id, data, actor)
