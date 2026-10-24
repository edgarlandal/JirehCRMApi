from sqlalchemy import Boolean, CheckConstraint, Index, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.crm_base import CRMRecord


class Service(CRMRecord, Base):
    __tablename__ = "services"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true(), index=True
    )

    tickets = relationship(
        "Ticket", back_populates="service", lazy="raise", passive_deletes="all"
    )

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_services_name_nonempty"),
        Index("ix_services_created_at_id", "created_at", "id"),
    )
