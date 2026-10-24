from datetime import datetime, timezone
from typing import Generic, TypeVar
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.crm_enums import CustomerStatus
from app.models.user import User, UserRole
from app.repositories.contact import ContactRepository
from app.repositories.customer import CustomerRepository
from app.repositories.service import ServiceRepository
from app.repositories.user import UserRepository
from app.schemas.crm_base import CRMFilters, CRMResponse
from app.schemas.pagination import PaginateResponse

Record = TypeVar("Record")


def integrity_conflict(exc: IntegrityError) -> None:
    """Translate known constraint failures only; connection/other DB errors propagate."""
    original = exc.orig
    code = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    sqlite_code = getattr(original, "sqlite_errorname", None)
    messages = {
        "23505": "A record with these unique values already exists",
        "23503": "A referenced record changed or is still in use",
        "23514": "The operation violates a data constraint",
        "23502": "A required value is missing",
        "SQLITE_CONSTRAINT_UNIQUE": "A record with these unique values already exists",
        "SQLITE_CONSTRAINT_FOREIGNKEY": "A referenced record changed or is still in use",
        "SQLITE_CONSTRAINT_CHECK": "The operation violates a data constraint",
        "SQLITE_CONSTRAINT_TRIGGER": "The operation violates a data constraint",
        "SQLITE_CONSTRAINT_NOTNULL": "A required value is missing",
    }
    message = messages.get(code) or messages.get(sqlite_code)
    if message:
        raise HTTPException(status_code=409, detail=message) from exc
    raise exc


def utc(value: datetime) -> datetime:
    # SQLite test storage loses timezone info. PostgreSQL returns aware timestamps.
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


class CRMService(Generic[Record]):
    response_schema: type[CRMResponse]
    catalog = False

    def __init__(self, repo):
        self.repo = repo
        self.customers = CustomerRepository(repo.db)
        self.contacts = ContactRepository(repo.db)
        self.users = UserRepository(repo.db)
        self.catalog_repo = ServiceRepository(repo.db)

    def scope(self, actor: User) -> UUID | None:
        if not actor.is_active or actor.role not in (UserRole.ADMIN, UserRole.USER):
            raise HTTPException(
                status_code=403, detail="An active CRM user is required"
            )
        return None if actor.role == UserRole.ADMIN or self.catalog else actor.id

    def require_admin(self, actor: User) -> None:
        self.scope(actor)
        if actor.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403, detail="Administrator access is required"
            )

    async def get_by_id(self, record_id: UUID, actor: User) -> Record:
        record = await self.repo.get_by_id(record_id, owner_id=self.scope(actor))
        if record is None:
            # Same response for missing and inaccessible IDs.
            raise HTTPException(status_code=404, detail="Resource not found")
        return record

    async def get_all(self, filters: CRMFilters, actor: User) -> PaginateResponse:
        records, total = await self.repo.get_all(filters, owner_id=self.scope(actor))
        return PaginateResponse[self.response_schema](
            items=[self.response_schema.model_validate(row) for row in records],
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def _create_record(self, record: Record) -> Record:
        try:
            return await self.repo.create(record)
        except IntegrityError as exc:
            integrity_conflict(exc)

    async def _update_record(self, record: Record, values: dict) -> Record:
        try:
            return await self.repo.update(record, values)
        except IntegrityError as exc:
            integrity_conflict(exc)

    async def validate_assignee(self, user_id: UUID | None) -> None:
        if user_id is None:
            return
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Assigned user not found")
        if not user.is_active:
            raise HTTPException(status_code=422, detail="Assigned user must be active")

    async def validate_customer(
        self, customer_id: UUID, actor: User, *, creating=False
    ):
        customer = await self.customers.get_by_id(
            customer_id, owner_id=self.scope(actor)
        )
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        if creating and customer.status == CustomerStatus.INACTIVE:
            raise HTTPException(
                status_code=409,
                detail="Reactivate the customer before adding resources",
            )
        return customer

    async def validate_links(self, values: dict, actor: User, record=None) -> None:
        customer_id = (
            record.customer_id if record is not None else values["customer_id"]
        )
        await self.validate_customer(customer_id, actor, creating=record is None)
        contact_id = values.get("contact_id", getattr(record, "contact_id", None))
        if contact_id is not None:
            contact = await self.contacts.get_by_id(
                contact_id, owner_id=self.scope(actor)
            )
            if contact is None:
                raise HTTPException(status_code=404, detail="Contact not found")
            if contact.customer_id != customer_id:
                raise HTTPException(
                    status_code=422, detail="Contact must belong to this customer"
                )
            if not contact.is_active and (
                record is None or contact_id != getattr(record, "contact_id", None)
            ):
                raise HTTPException(
                    status_code=422, detail="New associations require an active contact"
                )
        if "assigned_to_id" in values:
            await self.validate_assignee(values["assigned_to_id"])
        if values.get("service_id") is not None:
            service = await self.catalog_repo.get_by_id(values["service_id"])
            if service is None:
                raise HTTPException(status_code=404, detail="Service not found")
            if not service.is_active and (
                record is None or values["service_id"] != record.service_id
            ):
                raise HTTPException(
                    status_code=422, detail="New associations require an active service"
                )
