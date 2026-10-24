from typing import Annotated
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.crm_base import CRMFilters, CRMInput, CRMPatch, CRMResponse, Name


class ContactCreate(CRMInput):
    customer_id: UUID
    firstname: Name
    lastname: Name | None = None
    email: Annotated[EmailStr, Field(max_length=255)] | None = None
    phone: Annotated[str, Field(min_length=1, max_length=50)] | None = None
    position: Name | None = None
    is_active: bool = True


class ContactUpdate(CRMPatch):
    nonnullable = {"firstname", "is_active"}
    firstname: Name | None = None
    lastname: Name | None = None
    email: Annotated[EmailStr, Field(max_length=255)] | None = None
    phone: Annotated[str, Field(min_length=1, max_length=50)] | None = None
    position: Name | None = None
    is_active: bool | None = None


class ContactResponse(CRMResponse):
    customer_id: UUID
    firstname: Name
    lastname: Name | None
    email: Annotated[EmailStr, Field(max_length=255)] | None
    phone: Annotated[str, Field(min_length=1, max_length=50)] | None
    position: Name | None
    is_active: bool


class ContactFilters(CRMFilters):
    customer_id: UUID | None = None
    is_active: bool | None = None
    search: Annotated[str, Field(min_length=1, max_length=255)] | None = None
