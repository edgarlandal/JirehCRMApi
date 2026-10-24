from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import get_auth_service
from app.core.rate_limit import limiter
from app.schemas.auth import LogoutRequest, RefreshTokenRequest, TokenRespose
from app.schemas.user import UserCreate, UserReponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenRespose)
@limiter.limit("5/minute")
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    tokens = await auth_service.authenticate_user(
        form_data.username, form_data.password
    )
    return tokens


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    data: LogoutRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    await auth_service.logout(refresh_token=data.refresh_token)
    return {"detail": "Successfully logged out"}


@router.post("/refresh", response_model=TokenRespose)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    body: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    tokens = await auth_service.refresh_access_token(body.refresh_token)
    return tokens


@router.post(
    "/register", response_model=UserReponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("3/hour")
async def register_user(
    request: Request,
    user_data: UserCreate,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    created_user = await auth_service.register_user(user_data)
    return created_user
