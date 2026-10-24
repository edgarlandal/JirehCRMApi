from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import ActiveUser, get_service_catalog_service
from app.schemas.pagination import PaginateResponse
from app.schemas.service import (
    ServiceCreate,
    ServiceFilters,
    ServiceResponse,
    ServiceUpdate,
)
from app.services.service_catalog import ServiceCatalogService

router = APIRouter(prefix="/services", tags=["Service catalog"])
ServiceDependency = Annotated[
    ServiceCatalogService, Depends(get_service_catalog_service)
]


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    data: ServiceCreate,
    actor: ActiveUser,
    service: ServiceDependency,
):
    return await service.create(data, actor)


@router.get("", response_model=PaginateResponse[ServiceResponse])
async def list_services(
    filters: Annotated[ServiceFilters, Query()],
    actor: ActiveUser,
    service: ServiceDependency,
):
    return await service.get_all(filters, actor)


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: UUID,
    actor: ActiveUser,
    service: ServiceDependency,
):
    return await service.get_by_id(service_id, actor)


@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: UUID,
    data: ServiceUpdate,
    actor: ActiveUser,
    service: ServiceDependency,
):
    return await service.update(service_id, data, actor)


@router.post("/{service_id}/deactivate", response_model=ServiceResponse)
async def deactivate_service(
    service_id: UUID,
    actor: ActiveUser,
    service: ServiceDependency,
):
    return await service.deactivate(service_id, actor)
