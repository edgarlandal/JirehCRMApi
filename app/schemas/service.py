from typing import Annotated

from pydantic import Field

from app.schemas.crm_base import (
    Content,
    CRMFilters,
    CRMInput,
    CRMPatch,
    CRMResponse,
    Name,
)


class ServiceCreate(CRMInput):
    name: Name
    description: Content | None = None
    category: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    is_active: bool = True


class ServiceUpdate(CRMPatch):
    nonnullable = {"name", "is_active"}
    name: Name | None = None
    description: Content | None = None
    category: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    is_active: bool | None = None


class ServiceResponse(CRMResponse):
    name: Name
    description: Content | None
    category: Annotated[str, Field(min_length=1, max_length=100)] | None
    is_active: bool


class ServiceFilters(CRMFilters):
    is_active: bool | None = None
    search: Annotated[str, Field(min_length=1, max_length=255)] | None = None
