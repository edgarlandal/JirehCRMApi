from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    limit: int = Field(
        default=20, ge=1, le=100, description="Numbers of register a return (Max: 100)"
    )
    offset: int = Field(default=0, ge=0, description="Numbers of register to omit")


class PaginateResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return (self.offset + self.limit) < self.total
