import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Text,
    true,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.crm_base import CRMRecord


class TicketComment(CRMRecord, Base):
    __tablename__ = "ticket_comments"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )

    ticket = relationship(
        "Ticket", back_populates="comments", lazy="raise", passive_deletes="all"
    )
    author_user = relationship(
        "User", back_populates="ticket_comments", lazy="raise", passive_deletes="all"
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(body)) > 0", name="ck_ticket_comments_body_nonempty"
        ),
        Index("ix_ticket_comments_created_at_id", "created_at", "id"),
    )
