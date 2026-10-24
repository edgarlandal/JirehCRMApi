import uuid

from sqlalchemy import (
    CheckConstraint,
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
from app.models.crm_enums import CustomerStatus, CustomerType


class Customer(CRMRecord, Base):
    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_type: Mapped[CustomerType] = mapped_column(
        Enum(CustomerType, name="crm_customer_type_enum"), nullable=False
    )
    status: Mapped[CustomerStatus] = mapped_column(
        Enum(CustomerStatus, name="crm_customer_status_enum"),
        nullable=False,
        default=CustomerStatus.PROSPECT,
        server_default="PROSPECT",
        index=True,
    )
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    assigned_to = relationship(
        "User",
        back_populates="assigned_customers",
        lazy="raise",
        passive_deletes="all",
        foreign_keys="Customer.assigned_to_id",
    )
    created_by = relationship(
        "User",
        back_populates="created_customers",
        lazy="raise",
        passive_deletes="all",
        foreign_keys="Customer.created_by_id",
    )
    contacts = relationship(
        "Contact", back_populates="customer", lazy="raise", passive_deletes="all"
    )
    interactions = relationship(
        "Interaction", back_populates="customer", lazy="raise", passive_deletes="all"
    )
    appointments = relationship(
        "Appointment", back_populates="customer", lazy="raise", passive_deletes="all"
    )
    tickets = relationship(
        "Ticket", back_populates="customer", lazy="raise", passive_deletes="all"
    )

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_customers_name_nonempty"),
        Index("ix_customers_created_at_id", "created_at", "id"),
    )
