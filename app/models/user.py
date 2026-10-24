import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )

    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    firstname: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    lastname: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum"), default=UserRole.USER, nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    __table_args__ = (Index("idx_users_email_is_active", "email", "is_active"),)

    assigned_customers = relationship(
        "Customer",
        back_populates="assigned_to",
        lazy="raise",
        passive_deletes="all",
        foreign_keys="Customer.assigned_to_id",
    )

    created_customers = relationship(
        "Customer",
        back_populates="created_by",
        lazy="raise",
        passive_deletes="all",
        foreign_keys="Customer.created_by_id",
    )

    interactions = relationship(
        "Interaction", back_populates="created_by", lazy="raise", passive_deletes="all"
    )

    assigned_appointments = relationship(
        "Appointment",
        back_populates="assigned_to",
        lazy="raise",
        passive_deletes="all",
        foreign_keys="Appointment.assigned_to_id",
    )

    created_appointments = relationship(
        "Appointment",
        back_populates="created_by",
        lazy="raise",
        passive_deletes="all",
        foreign_keys="Appointment.created_by_id",
    )

    assigned_tickets = relationship(
        "Ticket",
        back_populates="assigned_to",
        lazy="raise",
        passive_deletes="all",
        foreign_keys="Ticket.assigned_to_id",
    )

    created_tickets = relationship(
        "Ticket",
        back_populates="created_by",
        lazy="raise",
        passive_deletes="all",
        foreign_keys="Ticket.created_by_id",
    )

    ticket_comments = relationship(
        "TicketComment",
        back_populates="author_user",
        lazy="raise",
        passive_deletes="all",
    )
