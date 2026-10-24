import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.crm_base import CRMRecord
from app.models.crm_enums import InteractionChannel


class Interaction(CRMRecord, Base):
    __tablename__ = "interactions"

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
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    channel: Mapped[InteractionChannel] = mapped_column(
        Enum(InteractionChannel, name="crm_interaction_channel_enum"), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    customer = relationship(
        "Customer", back_populates="interactions", lazy="raise", passive_deletes="all"
    )
    contact = relationship(
        "Contact", back_populates="interactions", lazy="raise", passive_deletes="all"
    )
    created_by = relationship(
        "User", back_populates="interactions", lazy="raise", passive_deletes="all"
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(summary)) > 0", name="ck_interactions_summary_nonempty"
        ),
        Index("ix_interactions_created_at_id", "created_at", "id"),
    )
