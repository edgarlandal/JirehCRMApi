from datetime import datetime, timezone
from typing import Annotated, ClassVar
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.schemas.pagination import PaginationParams


def as_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


UTCDateTime = Annotated[AwareDatetime, AfterValidator(as_utc)]
Name = Annotated[str, Field(min_length=1, max_length=255)]
Content = Annotated[str, Field(min_length=1, max_length=20000)]


class CRMInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CRMPatch(CRMInput):
    nonnullable: ClassVar[set[str]] = set()

    @model_validator(mode="after")
    def reject_explicit_null(self):
        for field in self.model_fields_set & self.nonnullable:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class CRMResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class CRMFilters(PaginationParams, CRMInput):
    created_from: UTCDateTime | None = None
    created_until: UTCDateTime | None = None

    @model_validator(mode="after")
    def validate_date_ranges(self):
        for start, end in (
            ("created_from", "created_until"),
            ("occurred_from", "occurred_until"),
            ("starts_from", "starts_until"),
        ):
            low, high = getattr(self, start, None), getattr(self, end, None)
            if low is not None and high is not None and low > high:
                raise ValueError(f"{start} must not be after {end}")
        return self
