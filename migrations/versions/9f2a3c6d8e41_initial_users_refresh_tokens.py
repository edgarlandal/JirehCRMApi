"""Initial users and refresh token schema."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f2a3c6d8e41"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("firstname", sa.String(length=255), nullable=False),
        sa.Column("lastname", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "USER", name="user_role_enum"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_users_email_is_active", "users", ["email", "is_active"], unique=False
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_firstname"), "users", ["firstname"], unique=False)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=True)
    op.create_index(op.f("ix_users_lastname"), "users", ["lastname"], unique=False)
    op.create_table(
        "refresh_token",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("user_email", sa.String(length=255), nullable=False),
        sa.Column("family_id", sa.String(length=36), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_email"], ["users.email"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_refresh_token_family_id"),
        "refresh_token",
        ["family_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_refresh_token_token_hash"),
        "refresh_token",
        ["token_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_refresh_token_token_hash"), table_name="refresh_token")
    op.drop_index(op.f("ix_refresh_token_family_id"), table_name="refresh_token")
    op.drop_table("refresh_token")
    op.drop_index(op.f("ix_users_lastname"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_firstname"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index("idx_users_email_is_active", table_name="users")
    op.drop_table("users")
