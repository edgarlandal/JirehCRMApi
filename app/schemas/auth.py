from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    email: EmailStr | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenRespose(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    model_config = ConfigDict(from_attributes=True)
