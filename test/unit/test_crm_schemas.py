from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.schemas.contact import ContactUpdate
from app.schemas.customer import CustomerCreate, CustomerFilters, CustomerUpdate
from app.schemas.interaction import InteractionUpdate
from app.schemas.service import ServiceUpdate
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.schemas.ticket_comment import TicketCommentCreate, TicketCommentUpdate


@pytest.mark.parametrize(
    "schema,field",
    [
        (CustomerUpdate, "name"),
        (CustomerUpdate, "customer_type"),
        (CustomerUpdate, "status"),
        (ContactUpdate, "firstname"),
        (ContactUpdate, "is_active"),
        (ServiceUpdate, "name"),
        (ServiceUpdate, "is_active"),
        (InteractionUpdate, "summary"),
        (InteractionUpdate, "channel"),
        (InteractionUpdate, "occurred_at"),
        (AppointmentUpdate, "assigned_to_id"),
        (AppointmentUpdate, "starts_at"),
        (AppointmentUpdate, "ends_at"),
        (AppointmentUpdate, "title"),
        (AppointmentUpdate, "status"),
        (TicketUpdate, "subject"),
        (TicketUpdate, "description"),
        (TicketUpdate, "priority"),
        (TicketUpdate, "status"),
        (TicketCommentUpdate, "body"),
        (TicketCommentUpdate, "is_internal"),
    ],
)
def test_patch_distinguishes_omitted_from_null(schema, field):
    assert schema().model_dump(exclude_unset=True) == {}
    with pytest.raises(ValidationError):
        schema(**{field: None})


@pytest.mark.parametrize(
    "schema,field",
    [
        (CustomerUpdate, "name"),
        (ContactUpdate, "firstname"),
        (ServiceUpdate, "name"),
        (InteractionUpdate, "summary"),
        (AppointmentUpdate, "title"),
        (TicketUpdate, "subject"),
        (TicketUpdate, "description"),
        (TicketCommentUpdate, "body"),
    ],
)
def test_required_text_rejects_whitespace(schema, field):
    with pytest.raises(ValidationError):
        schema(**{field: " \t\n "})


def test_nullable_fields_false_and_lengths():
    assert ContactUpdate(email=None, is_active=False).model_dump(
        exclude_unset=True
    ) == {
        "email": None,
        "is_active": False,
    }
    for payload in (
        {"email": "invalid"},
        {"firstname": "x" * 256},
        {"phone": "1" * 51},
    ):
        with pytest.raises(ValidationError):
            ContactUpdate(**payload)
    with pytest.raises(ValidationError):
        AppointmentUpdate(meeting_url="javascript:alert(1)")


@pytest.mark.parametrize(
    "schema,payload",
    [
        (
            CustomerCreate,
            {"name": "ACME", "customer_type": "COMPANY", "created_by_id": uuid4()},
        ),
        (
            TicketCreate,
            {
                "customer_id": uuid4(),
                "subject": "Support",
                "description": "Issue",
                "status": "CLOSED",
            },
        ),
        (TicketUpdate, {"resolved_at": datetime.now(timezone.utc)}),
        (TicketUpdate, {"closed_at": None}),
        (TicketUpdate, {"customer_id": uuid4()}),
        (ContactUpdate, {"customer_id": uuid4()}),
        (
            TicketCommentCreate,
            {"ticket_id": uuid4(), "body": "Note", "author_user_id": uuid4()},
        ),
        (TicketCommentUpdate, {"ticket_id": uuid4()}),
    ],
)
def test_internal_and_parent_fields_cannot_be_overridden(schema, payload):
    with pytest.raises(ValidationError):
        schema(**payload)


def test_datetimes_require_timezone_and_normalize_utc():
    with pytest.raises(ValidationError):
        AppointmentUpdate(starts_at="2026-10-23T12:00:00")
    patch = AppointmentUpdate(starts_at="2026-10-23T12:00:00-07:00")
    assert patch.starts_at == datetime(2026, 10, 23, 19, tzinfo=timezone.utc)
    assert patch.starts_at.utcoffset() == timedelta(0)
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        AppointmentCreate(
            customer_id=uuid4(),
            assigned_to_id=uuid4(),
            title="Visit",
            starts_at=now,
            ends_at=now,
        )


def test_pagination_and_date_bounds():
    for payload in (
        {"limit": 101},
        {"limit": 0},
        {"offset": -1},
        {
            "created_from": "2026-10-24T00:00:00Z",
            "created_until": "2026-10-23T00:00:00Z",
        },
    ):
        with pytest.raises(ValidationError):
            CustomerFilters(**payload)
