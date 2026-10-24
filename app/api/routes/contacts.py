from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import ActiveUser, get_contact_service
from app.schemas.contact import (
    ContactCreate,
    ContactFilters,
    ContactResponse,
    ContactUpdate,
)
from app.schemas.pagination import PaginateResponse
from app.services.contact import ContactService

router = APIRouter(prefix="/contacts", tags=["Contact"])
ContactDependency = Annotated[ContactService, Depends(get_contact_service)]


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: ContactCreate,
    actor: ActiveUser,
    service: ContactDependency,
):
    return await service.create(data, actor)


@router.get("", response_model=PaginateResponse[ContactResponse])
async def list_contacts(
    filters: Annotated[ContactFilters, Query()],
    actor: ActiveUser,
    service: ContactDependency,
):
    return await service.get_all(filters, actor)


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: UUID,
    actor: ActiveUser,
    service: ContactDependency,
):
    return await service.get_by_id(contact_id, actor)


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: UUID,
    data: ContactUpdate,
    actor: ActiveUser,
    service: ContactDependency,
):
    return await service.update(contact_id, data, actor)


@router.post("/{contact_id}/deactivate", response_model=ContactResponse)
async def deactivate_contact(
    contact_id: UUID,
    actor: ActiveUser,
    service: ContactDependency,
):
    return await service.deactivate(contact_id, actor)
