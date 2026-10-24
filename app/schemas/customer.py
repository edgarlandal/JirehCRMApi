from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.models.crm_enums import CustomerStatus, CustomerType
from app.schemas.crm_base import (
    Content,
    CRMFilters,
    CRMInput,
    CRMPatch,
    CRMResponse,
    Name,
)


class CustomerCreate(CRMInput):
    name: Name
    customer_type: CustomerType
    status: CustomerStatus = CustomerStatus.PROSPECT
    tax_id: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    notes: Content | None = None
    assigned_to_id: UUID | None = None


class CustomerUpdate(CRMPatch):
    nonnullable = {"name", "customer_type", "status"}
    name: Name | None = None
    customer_type: CustomerType | None = None
    status: CustomerStatus | None = None
    tax_id: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    notes: Content | None = None
    assigned_to_id: UUID | None = None


class CustomerResponse(CRMResponse):
    name: Name
    customer_type: CustomerType
    status: CustomerStatus
    tax_id: Annotated[str, Field(min_length=1, max_length=64)] | None
    notes: Content | None
    assigned_to_id: UUID | None
    created_by_id: UUID


class CustomerFilters(CRMFilters):
    customer_type: CustomerType | None = None
    status: CustomerStatus | None = None
    assigned_to_id: UUID | None = None
    search: Annotated[str, Field(min_length=1, max_length=255)] | None = None
