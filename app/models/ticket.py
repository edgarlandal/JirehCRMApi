import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.crm_base import CRMRecord
from app.models.crm_enums import TicketPriority, TicketStatus


class Ticket(CRMRecord, Base):
    __tablename__ = "tickets"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="crm_ticket_status_enum"),
        nullable=False,
        default=TicketStatus.OPEN,
        server_default="OPEN",
        index=True,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, name="crm_ticket_priority_enum"),
        nullable=False,
        default=TicketPriority.NORMAL,
        server_default="NORMAL",
        index=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    customer = relationship(
        "Customer", back_populates="tickets", lazy="raise", passive_deletes="all"
    )
    contact = relationship(
        "Contact", back_populates="tickets", lazy="raise", passive_deletes="all"
    )
    service = relationship(
        "Service", back_populates="tickets", lazy="raise", passive_deletes="all"
    )
    assigned_to = relationship(
        "User",
        back_populates="assigned_tickets",
        lazy="raise",
        passive_deletes="all",
        foreign_keys="Ticket.assigned_to_id",
    )
    created_by = relationship(
        "User",
        back_populates="created_tickets",
        lazy="raise",
        passive_deletes="all",
        foreign_keys="Ticket.created_by_id",
    )
    comments = relationship(
        "TicketComment", back_populates="ticket", lazy="raise", passive_deletes="all"
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(subject)) > 0", name="ck_tickets_subject_nonempty"
        ),
        CheckConstraint(
            "length(trim(description)) > 0", name="ck_tickets_description_nonempty"
        ),
        CheckConstraint(
            "(status IN ('OPEN', 'IN_PROGRESS', 'WAITING_CUSTOMER') AND resolved_at IS NULL AND closed_at IS NULL) OR (status = 'RESOLVED' AND resolved_at IS NOT NULL AND closed_at IS NULL) OR (status = 'CLOSED' AND resolved_at IS NOT NULL AND closed_at IS NOT NULL AND closed_at >= resolved_at)",
            name="ck_tickets_resolution",
        ),
        Index("ix_tickets_created_at_id", "created_at", "id"),
    )
