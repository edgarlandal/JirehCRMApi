from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import ActiveUser, get_customer_service
from app.schemas.customer import (
    CustomerCreate,
    CustomerFilters,
    CustomerResponse,
    CustomerUpdate,
)
from app.schemas.pagination import PaginateResponse
from app.services.customer import CustomerService

router = APIRouter(prefix="/customers", tags=["Customer"])
CustomerDependency = Annotated[CustomerService, Depends(get_customer_service)]


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    data: CustomerCreate,
    actor: ActiveUser,
    service: CustomerDependency,
):
    return await service.create(data, actor)


@router.get("", response_model=PaginateResponse[CustomerResponse])
async def list_customers(
    filters: Annotated[CustomerFilters, Query()],
    actor: ActiveUser,
    service: CustomerDependency,
):
    return await service.get_all(filters, actor)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    actor: ActiveUser,
    service: CustomerDependency,
):
    return await service.get_by_id(customer_id, actor)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: UUID,
    data: CustomerUpdate,
    actor: ActiveUser,
    service: CustomerDependency,
):
    return await service.update(customer_id, data, actor)


@router.post("/{customer_id}/archive", response_model=CustomerResponse)
async def archive_customer(
    customer_id: UUID,
    actor: ActiveUser,
    service: CustomerDependency,
):
    return await service.archive(customer_id, actor)
