import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from loguru import logger

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_acces_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate


class AuthService:
    def __init__(
        self, user_repo: UserRepository, refresh_repo: RefreshTokenRepository = None
    ):
        self.user_repo = user_repo
        self.refresh_repo = refresh_repo

    async def authenticate_user(self, email: str, password: str) -> dict:
        user = await self.user_repo.get_by_email(email)

        if not user or not verify_password(password, user.hashed_password):
            logger.warning(
                "Authentication attempt failed: Invalid credentials",
                event="auth.login_failed",
                reason="invalid_credentials",
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalids Credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if getattr(user, "disabled", False) or not getattr(user, "is_active", True):
            logger.warning(
                "login_failed", event="auth.login_failed", reason="inactive_account"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user account"
            )

        user.last_login_at = datetime.now(timezone.utc)
        await self.user_repo.save(user)

        family_id = str(uuid.uuid4())
        access_token = create_access_token({"sub": user.email})
        refresh_token = create_refresh_token(
            {"sub": user.email, "family_id": family_id}
        )

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        await self.refresh_repo.create(
            user_email=user.email,
            token_hash=hash_token(refresh_token),
            family_id=family_id,
            expires_at=expires_at,
        )

        logger.info(
            "login_succeeded", event="auth.login_succeeded", user_id=str(user.id)
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def refresh_access_token(self, refresh_token: str) -> dict:
        payload = decode_acces_token(refresh_token, expected_type="refresh")
        email = payload.get("sub")

        token_hash = hash_token(refresh_token)
        db_token = await self.refresh_repo.get_by_hash(token_hash)

        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or untrusted refresh token",
            )

        if db_token.used_at is not None or db_token.revoked:
            await self.refresh_repo.revoke_family(db_token.family_id)
            logger.warning(
                "refresh_reuse", event="auth.refresh_reuse", reason="sessions_revoked"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Security alert: Refresh token reuse detected. All sessions revoked.",
            )

        if db_token.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
            )

        user = await self.user_repo.get_by_email(email)
        if (
            not user
            or getattr(user, "disabled", False)
            or not getattr(user, "is_active", True)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        await self.refresh_repo.mark_as_used(db_token.id)

        new_access_token = create_access_token(data={"sub": user.email})
        new_refresh_token = create_refresh_token(
            data={"sub": user.email, "family_id": db_token.family_id}
        )

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        await self.refresh_repo.create(
            user_email=user.email,
            token_hash=hash_token(new_refresh_token),
            family_id=db_token.family_id,
            expires_at=expires_at,
        )

        logger.info(
            "refresh_succeeded", event="auth.refresh_succeeded", user_id=str(user.id)
        )
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    async def register_user(self, user_in: UserCreate) -> User:
        existing = await self.user_repo.get_by_email(user_in.email)

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email exist"
            )

        db_user = User(
            email=user_in.email,
            hashed_password=hash_password(user_in.password),
            firstname=user_in.firstname,
            lastname=user_in.lastname,
        )

        return await self.user_repo.create(db_user)

    async def logout(self, refresh_token: str) -> None:
        hashed_rt = hash_token(refresh_token)
        db_token = await self.refresh_repo.get_by_hash(hashed_rt)

        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired refresh token",
            )

        if db_token.revoked:
            return

        await self.refresh_repo.revoke(hashed_rt)
        logger.info("logout_succeeded", event="auth.logout_succeeded")
