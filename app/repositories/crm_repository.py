from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.ticket import Ticket
from app.repositories.base_repository import BaseRepository
from app.schemas.crm_base import CRMFilters

Record = TypeVar("Record")


class CRMRepository(BaseRepository[Record], Generic[Record]):
    """Persistence only. The service supplies the authorized customer owner scope.

    Responses contain scalar fields; all ORM relationships use lazy='raise'.
    No implicit relationship IO is needed for response serialization.
    Like UserRepository, this layer owns commit/rollback for each mutation.
    """

    search_fields: tuple[str, ...] = ()

    def __init__(self, model: type[Record], db: AsyncSession):
        super().__init__(model, db)
        self.db = db

    def query(self, owner_id: UUID | None = None):
        query = select(self.model)
        if owner_id is not None:
            if self.model is Customer:
                query = query.where(Customer.assigned_to_id == owner_id)
            elif self.model.__tablename__ == "ticket_comments":
                query = (
                    query.join(Ticket, self.model.ticket_id == Ticket.id)
                    .join(Customer, Ticket.customer_id == Customer.id)
                    .where(Customer.assigned_to_id == owner_id)
                )
            else:
                query = query.join(
                    Customer, self.model.customer_id == Customer.id
                ).where(Customer.assigned_to_id == owner_id)
        return query

    async def get_by_id(
        self, record_id: UUID, *, owner_id: UUID | None = None
    ) -> Record | None:
        result = await self.db.execute(
            self.query(owner_id).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, filters: CRMFilters, *, owner_id: UUID | None = None):
        query = self.query(owner_id)
        values = filters.model_dump(exclude_none=True, exclude={"limit", "offset"})
        date_fields = {
            "created_from": ("created_at", True),
            "created_until": ("created_at", False),
            "occurred_from": ("occurred_at", True),
            "occurred_until": ("occurred_at", False),
            "starts_from": ("starts_at", True),
            "starts_until": ("starts_at", False),
        }
        for name, value in values.items():
            if name == "search":
                # Escape wildcard characters so search is a literal substring.
                escaped = (
                    value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                )
                query = query.where(
                    or_(
                        *(
                            getattr(self.model, field).ilike(
                                f"%{escaped}%", escape="\\"
                            )
                            for field in self.search_fields
                        )
                    )
                )
            elif name in date_fields:
                field, lower = date_fields[name]
                column = getattr(self.model, field)
                query = query.where(column >= value if lower else column <= value)
            else:
                query = query.where(getattr(self.model, name) == value)
        query = query.order_by(self.model.created_at.desc(), self.model.id.desc())
        # Defend the bound even if a caller bypasses Pydantic validation.
        return await self.get_pagination(
            query, min(max(filters.limit, 1), 100), max(filters.offset, 0)
        )

    async def create(self, record: Record) -> Record:
        return await self.save(record)

    async def save(self, record: Record) -> Record:
        try:
            self.db.add(record)
            await self.db.commit()
            await self.db.refresh(record)
            return record
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def update(self, record: Record, values: dict) -> Record:
        for name, value in values.items():
            setattr(record, name, value)
        return await self.save(record)
