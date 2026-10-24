import re
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    firstname: str
    lastname: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("firstname", "lastname")
    @classmethod
    def clean_names(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("The value can't empty")

        return cleaned


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_policy(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("The password must be at least 8 character long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("It must include at least one capital letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("It must include at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("It must include at least one number")
        return v


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    firstname: str | None = Field(default=None, min_length=1)
    lastname: str | None = Field(default=None, min_length=1)

    @field_validator("firstname", "lastname", mode="before")
    @classmethod
    def reject_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("El valor no puede ser null.")
        return value


class UserAdminUpdate(UserProfileUpdate):
    is_active: bool | None = None
    is_verified: bool | None = None
    role: UserRole | None = None

    @field_validator("is_active", "is_verified", "role", mode="before")
    @classmethod
    def reject_admin_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("El valor no puede ser null.")
        return value


class UserReponse(UserBase):
    id: uuid.UUID
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
