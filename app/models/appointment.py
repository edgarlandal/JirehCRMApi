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
from app.models.crm_enums import AppointmentStatus


class Appointment(CRMRecord, Base):
    __tablename__ = "appointments"

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
    assigned_to_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="crm_appointment_status_enum"),
        nullable=False,
        default=AppointmentStatus.SCHEDULED,
        server_default="SCHEDULED",
        index=True,
    )
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meeting_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    customer = relationship(
        "Customer", back_populates="appointments", lazy="raise", passive_deletes="all"
    )
    contact = relationship(
        "Contact", back_populates="appointments", lazy="raise", passive_deletes="all"
    )
    assigned_to = relationship(
        "User",
        back_populates="assigned_appointments",
        lazy="raise",
        passive_deletes="all",
        foreign_keys="Appointment.assigned_to_id",
    )
    created_by = relationship(
        "User",
        back_populates="created_appointments",
        lazy="raise",
        passive_deletes="all",
        foreign_keys="Appointment.created_by_id",
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(title)) > 0", name="ck_appointments_title_nonempty"
        ),
        CheckConstraint("ends_at > starts_at", name="ck_appointments_interval"),
        Index("ix_appointments_created_at_id", "created_at", "id"),
    )
