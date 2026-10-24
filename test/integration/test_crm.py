from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import delete, event, inspect, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import selectinload

from app.models.appointment import Appointment
from app.models.contact import Contact
from app.models.crm_enums import CustomerStatus, TicketStatus
from app.models.customer import Customer
from app.models.interaction import Interaction
from app.models.service import Service
from app.models.ticket import Ticket
from app.models.ticket_comment import TicketComment
from app.models.user import User, UserRole
from app.repositories.appointment import AppointmentRepository
from app.repositories.contact import ContactRepository
from app.repositories.customer import CustomerRepository
from app.repositories.interaction import InteractionRepository
from app.repositories.service import ServiceRepository
from app.repositories.ticket import TicketRepository
from app.repositories.ticket_comment import TicketCommentRepository
from app.repositories.user import UserRepository
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentFilters,
    AppointmentResponse,
    AppointmentUpdate,
)
from app.schemas.contact import ContactCreate, ContactFilters, ContactUpdate
from app.schemas.customer import CustomerCreate, CustomerFilters, CustomerUpdate
from app.schemas.interaction import (
    InteractionCreate,
    InteractionFilters,
    InteractionUpdate,
)
from app.schemas.service import ServiceCreate, ServiceFilters
from app.schemas.ticket import TicketCreate, TicketFilters, TicketResponse, TicketUpdate
from app.schemas.ticket_comment import (
    TicketCommentCreate,
    TicketCommentFilters,
    TicketCommentUpdate,
)
from app.services.appointment import AppointmentService
from app.services.contact import ContactService
from app.services.customer import CustomerService
from app.services.interaction import InteractionService
from app.services.service_catalog import ServiceCatalogService
from app.services.ticket import TICKET_TRANSITIONS, TicketService
from app.services.ticket_comment import TicketCommentService
from app.services.user import UserService


@pytest_asyncio.fixture
async def crm(db_session, test_user, admin_user):
    services = SimpleNamespace(
        customer=CustomerService(CustomerRepository(db_session)),
        contact=ContactService(ContactRepository(db_session)),
        catalog=ServiceCatalogService(ServiceRepository(db_session)),
        interaction=InteractionService(InteractionRepository(db_session)),
        appointment=AppointmentService(AppointmentRepository(db_session)),
        ticket=TicketService(TicketRepository(db_session)),
        comment=TicketCommentService(TicketCommentRepository(db_session)),
    )
    customer = await services.customer.create(
        CustomerCreate(name="ACME", customer_type="COMPANY"), test_user
    )
    contact = await services.contact.create(
        ContactCreate(
            customer_id=customer.id, firstname="Ana", email="ana@example.com"
        ),
        test_user,
    )
    service = await services.catalog.create(
        ServiceCreate(name="IT Support"), admin_user
    )
    ticket = await services.ticket.create(
        TicketCreate(
            customer_id=customer.id,
            contact_id=contact.id,
            service_id=service.id,
            subject="Network",
            description="Offline",
            assigned_to_id=test_user.id,
        ),
        test_user,
    )
    comment = await services.comment.create(
        TicketCommentCreate(ticket_id=ticket.id, body="Investigating"), test_user
    )
    now = datetime.now(timezone.utc)
    interaction = await services.interaction.create(
        InteractionCreate(
            customer_id=customer.id,
            contact_id=contact.id,
            channel="CALL",
            summary="Initial call",
            occurred_at=now,
        ),
        test_user,
    )
    appointment = await services.appointment.create(
        AppointmentCreate(
            customer_id=customer.id,
            contact_id=contact.id,
            assigned_to_id=test_user.id,
            title="Diagnosis",
            starts_at=now,
            ends_at=now + timedelta(hours=1),
            meeting_url="https://example.com/meeting",
        ),
        test_user,
    )
    outsider = User(
        email="outsider@example.com",
        hashed_password="unused",
        firstname="Other",
        lastname="Employee",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(outsider)
    await db_session.commit()
    return SimpleNamespace(
        services=services,
        customer=customer,
        contact=contact,
        service=service,
        ticket=ticket,
        comment=comment,
        interaction=interaction,
        appointment=appointment,
        outsider=outsider,
    )


async def test_relationships_and_async_serialization(crm, db_session, test_user):
    stmt = (
        select(Customer)
        .where(Customer.id == crm.customer.id)
        .options(
            selectinload(Customer.contacts),
            selectinload(Customer.interactions),
            selectinload(Customer.appointments),
            selectinload(Customer.tickets).selectinload(Ticket.comments),
            selectinload(Customer.assigned_to),
            selectinload(Customer.created_by),
        )
    )
    customer = (await db_session.scalars(stmt)).one()
    assert customer.contacts[0].id == crm.contact.id
    assert customer.interactions[0].id == crm.interaction.id
    assert customer.appointments[0].id == crm.appointment.id
    assert customer.tickets[0].comments[0].id == crm.comment.id
    assert customer.assigned_to.id == customer.created_by.id == test_user.id
    for model in (
        Customer,
        Contact,
        Service,
        Interaction,
        Appointment,
        Ticket,
        TicketComment,
    ):
        for relation in inspect(model).relationships:
            assert relation.back_populates and relation.passive_deletes == "all"
            assert not relation.cascade.delete and relation.lazy == "raise"
    statements = []

    def record_sql(*args):
        statements.append(args[2])

    event.listen(db_session.bind.sync_engine, "before_cursor_execute", record_sql)
    try:
        assert TicketResponse.model_validate(crm.ticket).id == crm.ticket.id
        assert (
            AppointmentResponse.model_validate(crm.appointment).id == crm.appointment.id
        )
        assert not statements
    finally:
        event.remove(db_session.bind.sync_engine, "before_cursor_execute", record_sql)


async def test_partial_updates_preserve_false_and_clear_null(crm, test_user):
    contact = await crm.services.contact.update(
        crm.contact.id, ContactUpdate(email=None, is_active=False), test_user
    )
    assert (
        contact.email is None
        and contact.is_active is False
        and contact.firstname == "Ana"
    )
    comment = await crm.services.comment.update(
        crm.comment.id, TicketCommentUpdate(is_internal=False), test_user
    )
    assert comment.is_internal is False and comment.body == "Investigating"
    ticket = await crm.services.ticket.update(
        crm.ticket.id, TicketUpdate(contact_id=None, assigned_to_id=None), test_user
    )
    assert (
        ticket.contact_id is None
        and ticket.assigned_to_id is None
        and ticket.subject == "Network"
    )


@pytest.mark.parametrize(
    "resource,filters,update",
    [
        ("customer", CustomerFilters, CustomerUpdate(name="Forbidden")),
        ("contact", ContactFilters, ContactUpdate(firstname="Forbidden")),
        ("interaction", InteractionFilters, InteractionUpdate(summary="Forbidden")),
        ("appointment", AppointmentFilters, AppointmentUpdate(title="Forbidden")),
        ("ticket", TicketFilters, TicketUpdate(subject="Forbidden")),
        ("comment", TicketCommentFilters, TicketCommentUpdate(body="Forbidden")),
    ],
)
async def test_access_scopes_reads_writes_lists_and_admin(
    crm, test_user, admin_user, resource, filters, update
):
    service = getattr(crm.services, resource)
    record = getattr(crm, resource)
    for operation in (
        lambda: service.get_by_id(record.id, crm.outsider),
        lambda: service.update(record.id, update, crm.outsider),
    ):
        with pytest.raises(HTTPException) as exc:
            await operation()
        assert exc.value.status_code == 404
    page = await service.get_all(filters(), crm.outsider)
    assert page.total == 0 and page.items == []
    assert (await service.get_all(filters(), test_user)).total == 1
    assert (await service.get_all(filters(), admin_user)).total == 1
    assert (await service.get_by_id(record.id, admin_user)).id == record.id


async def test_comments_check_ticket_access_before_create_or_list(crm):
    for operation in (
        lambda: crm.services.comment.create(
            TicketCommentCreate(ticket_id=crm.ticket.id, body="Attack"), crm.outsider
        ),
        lambda: crm.services.comment.get_all(
            TicketCommentFilters(ticket_id=crm.ticket.id), crm.outsider
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await operation()
        assert exc.value.status_code == 404


async def test_customer_assignment_and_reassignment(crm, test_user, admin_user):
    customer = await crm.services.customer.create(
        CustomerCreate(
            name="Own", customer_type="PERSON", assigned_to_id=admin_user.id
        ),
        test_user,
    )
    assert customer.assigned_to_id == customer.created_by_id == test_user.id
    with pytest.raises(HTTPException) as exc:
        await crm.services.customer.update(
            customer.id, CustomerUpdate(assigned_to_id=admin_user.id), test_user
        )
    assert exc.value.status_code == 403
    await crm.services.customer.update(
        crm.customer.id, CustomerUpdate(assigned_to_id=crm.outsider.id), admin_user
    )
    assert (await crm.services.ticket.get_all(TicketFilters(), test_user)).total == 0
    assert (
        await crm.services.comment.get_all(TicketCommentFilters(), crm.outsider)
    ).total == 1


@pytest.mark.parametrize(
    "resource,create_schema,update_schema,extras",
    [
        (
            "ticket",
            TicketCreate,
            TicketUpdate,
            {"subject": "New", "description": "Details"},
        ),
        (
            "interaction",
            InteractionCreate,
            InteractionUpdate,
            {
                "channel": "NOTE",
                "summary": "Note",
                "occurred_at": datetime.now(timezone.utc),
            },
        ),
        (
            "appointment",
            AppointmentCreate,
            AppointmentUpdate,
            {
                "title": "Visit",
                "starts_at": datetime.now(timezone.utc),
                "ends_at": datetime.now(timezone.utc) + timedelta(hours=1),
            },
        ),
    ],
)
async def test_contact_must_belong_to_customer_on_create_and_update(
    crm, test_user, resource, create_schema, update_schema, extras
):
    other = await crm.services.customer.create(
        CustomerCreate(name="Other", customer_type="PERSON"), test_user
    )
    contact = await crm.services.contact.create(
        ContactCreate(customer_id=other.id, firstname="Other"), test_user
    )
    payload = dict(extras, customer_id=crm.customer.id, contact_id=contact.id)
    if resource == "appointment":
        payload["assigned_to_id"] = test_user.id
    service = getattr(crm.services, resource)
    with pytest.raises(HTTPException) as exc:
        await service.create(create_schema(**payload), test_user)
    assert exc.value.status_code == 422
    with pytest.raises(HTTPException) as exc:
        await service.update(
            getattr(crm, resource).id, update_schema(contact_id=contact.id), test_user
        )
    assert exc.value.status_code == 422


async def test_appointment_partial_interval_and_database_constraint(
    crm, test_user, db_session
):
    for patch in (
        AppointmentUpdate(starts_at=datetime.now(timezone.utc) + timedelta(days=1)),
        AppointmentUpdate(ends_at=datetime.now(timezone.utc) - timedelta(days=1)),
    ):
        with pytest.raises(HTTPException) as exc:
            await crm.services.appointment.update(crm.appointment.id, patch, test_user)
        assert exc.value.status_code == 422
    now = datetime.now(timezone.utc)
    updated = await crm.services.appointment.update(
        crm.appointment.id,
        AppointmentUpdate(
            starts_at=now, ends_at=now + timedelta(hours=2), meeting_url=None
        ),
        test_user,
    )
    assert updated.meeting_url is None
    db_session.add(
        Appointment(
            customer_id=crm.customer.id,
            assigned_to_id=test_user.id,
            created_by_id=test_user.id,
            title="Invalid",
            starts_at=now,
            ends_at=now,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.parametrize("source", list(TicketStatus))
@pytest.mark.parametrize("target", list(TicketStatus))
async def test_ticket_transition_matrix(crm, test_user, db_session, source, target):
    ticket = crm.ticket
    ticket.status = source
    now = datetime.now(timezone.utc)
    ticket.resolved_at = (
        now if source in (TicketStatus.RESOLVED, TicketStatus.CLOSED) else None
    )
    ticket.closed_at = now if source == TicketStatus.CLOSED else None
    await db_session.commit()
    if target != source and target not in TICKET_TRANSITIONS[source]:
        with pytest.raises(HTTPException) as exc:
            await crm.services.ticket.update(
                ticket.id, TicketUpdate(status=target), test_user
            )
        assert exc.value.status_code == 409
        return
    ticket = await crm.services.ticket.update(
        ticket.id, TicketUpdate(status=target), test_user
    )
    assert ticket.status == target
    assert (ticket.resolved_at is not None) == (
        target in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
    )
    assert (ticket.closed_at is not None) == (target == TicketStatus.CLOSED)
    if target == TicketStatus.CLOSED:
        assert ticket.closed_at >= ticket.resolved_at


async def test_catalog_permissions_and_disabled_associations(
    crm, test_user, admin_user, db_session
):
    assert (await crm.services.catalog.get_all(ServiceFilters(), test_user)).total == 1
    with pytest.raises(HTTPException) as exc:
        await crm.services.catalog.create(ServiceCreate(name="Forbidden"), test_user)
    assert exc.value.status_code == 403
    await crm.services.catalog.deactivate(crm.service.id, admin_user)
    assert (
        await crm.services.catalog.get_all(ServiceFilters(is_active=False), test_user)
    ).total == 1
    with pytest.raises(HTTPException) as exc:
        await crm.services.ticket.create(
            TicketCreate(
                customer_id=crm.customer.id,
                service_id=crm.service.id,
                subject="New",
                description="Details",
            ),
            test_user,
        )
    assert exc.value.status_code == 422
    await crm.services.ticket.update(
        crm.ticket.id,
        TicketUpdate(description="Existing association survives"),
        test_user,
    )
    crm.outsider.is_active = False
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await crm.services.ticket.update(
            crm.ticket.id, TicketUpdate(assigned_to_id=crm.outsider.id), test_user
        )
    assert exc.value.status_code == 422
    with pytest.raises(HTTPException) as exc:
        await crm.services.catalog.get_all(ServiceFilters(), crm.outsider)
    assert exc.value.status_code == 403


async def test_archive_preserves_history_and_blocks_new_resources(crm, test_user):
    await crm.services.customer.archive(crm.customer.id, test_user)
    assert (
        await crm.services.customer.get_all(
            CustomerFilters(status=CustomerStatus.INACTIVE), test_user
        )
    ).total == 1
    assert (
        await crm.services.ticket.get_by_id(crm.ticket.id, test_user)
    ).id == crm.ticket.id
    assert (
        await crm.services.comment.get_all(TicketCommentFilters(), test_user)
    ).total == 1
    assert (
        await crm.services.interaction.get_all(InteractionFilters(), test_user)
    ).total == 1
    with pytest.raises(HTTPException) as exc:
        await crm.services.contact.create(
            ContactCreate(customer_id=crm.customer.id, firstname="New"), test_user
        )
    assert exc.value.status_code == 409


@pytest.mark.parametrize("resource", ["customer", "contact", "service", "ticket"])
async def test_hard_delete_referenced_records_is_restricted(crm, db_session, resource):
    record = getattr(crm, resource)
    record_id, model = record.id, type(record)
    with pytest.raises(IntegrityError):
        await db_session.execute(delete(model).where(model.id == record_id))
        await db_session.commit()
    await db_session.rollback()
    assert await db_session.get(model, record_id) is not None


async def test_user_delete_returns_conflict_and_preserves_history(
    crm, test_user, db_session
):
    user_id, ticket_id = test_user.id, crm.ticket.id
    with pytest.raises(HTTPException) as exc:
        await UserService(UserRepository(db_session)).delete_user(user_id)
    assert exc.value.status_code == 409
    assert await db_session.get(Ticket, ticket_id) is not None
    assert await db_session.get(User, user_id) is not None


async def test_filters_pagination_are_deterministic_and_scoped(
    crm, test_user, admin_user
):
    for name in ("B", "C", "D"):
        await crm.services.customer.create(
            CustomerCreate(name=name, customer_type="PERSON"), test_user
        )
    await crm.services.customer.create(
        CustomerCreate(name="Hidden", customer_type="PERSON"), crm.outsider
    )
    first = await crm.services.customer.get_all(CustomerFilters(limit=2), test_user)
    second = await crm.services.customer.get_all(
        CustomerFilters(limit=2, offset=2), test_user
    )
    assert first.total == second.total == 4
    assert len({row.id for row in first.items + second.items}) == 4
    assert (
        await crm.services.customer.get_all(CustomerFilters(limit=2), test_user)
    ).items == first.items
    assert (
        await crm.services.customer.get_all(CustomerFilters(search="Hidden"), test_user)
    ).total == 0
    assert (
        await crm.services.customer.get_all(
            CustomerFilters(assigned_to_id=crm.outsider.id), test_user
        )
    ).total == 0
    assert (
        await crm.services.customer.get_all(CustomerFilters(search="ACME"), admin_user)
    ).total == 1
    assert (
        await crm.services.ticket.get_all(
            TicketFilters(
                customer_id=crm.customer.id,
                priority="NORMAL",
                status="OPEN",
                assigned_to_id=test_user.id,
            ),
            test_user,
        )
    ).total == 1
    assert (
        await crm.services.ticket.get_all(TicketFilters(priority="URGENT"), test_user)
    ).total == 0
    assert (
        await crm.services.interaction.get_all(
            InteractionFilters(
                occurred_from=datetime.now(timezone.utc) + timedelta(days=1)
            ),
            test_user,
        )
    ).total == 0
    assert (
        await crm.services.appointment.get_all(
            AppointmentFilters(
                starts_until=datetime.now(timezone.utc) - timedelta(days=1)
            ),
            test_user,
        )
    ).total == 0


async def test_missing_records_and_storage_errors_are_not_duplicates(
    crm, test_user, monkeypatch
):
    with pytest.raises(HTTPException) as exc:
        await crm.services.ticket.get_by_id(uuid4(), test_user)
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        await crm.services.ticket.update(
            crm.ticket.id, TicketUpdate(service_id=uuid4()), test_user
        )
    assert exc.value.status_code == 404
    error = OperationalError("statement", {}, RuntimeError("connection lost"))
    monkeypatch.setattr(
        crm.services.customer.repo, "create", AsyncMock(side_effect=error)
    )
    with pytest.raises(OperationalError):
        await crm.services.customer.create(
            CustomerCreate(name="Fail", customer_type="PERSON"), test_user
        )
