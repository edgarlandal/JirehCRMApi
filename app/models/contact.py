import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    true,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.crm_base import CRMRecord


class Contact(CRMRecord, Base):
    __tablename__ = "contacts"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    firstname: Mapped[str] = mapped_column(String(255), nullable=False)
    lastname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true(), index=True
    )

    customer = relationship(
        "Customer", back_populates="contacts", lazy="raise", passive_deletes="all"
    )
    interactions = relationship(
        "Interaction", back_populates="contact", lazy="raise", passive_deletes="all"
    )
    appointments = relationship(
        "Appointment", back_populates="contact", lazy="raise", passive_deletes="all"
    )
    tickets = relationship(
        "Ticket", back_populates="contact", lazy="raise", passive_deletes="all"
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(firstname)) > 0", name="ck_contacts_firstname_nonempty"
        ),
        Index("ix_contacts_created_at_id", "created_at", "id"),
    )
