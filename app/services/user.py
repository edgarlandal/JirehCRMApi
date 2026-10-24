from uuid import UUID

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.schemas.pagination import PaginateResponse, PaginationParams
from app.schemas.user import UserAdminUpdate, UserCreate, UserProfileUpdate, UserReponse
from app.services.crm_base import integrity_conflict


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register_user(self, user_data: UserCreate) -> User:
        existing_user = await self.user_repo.get_by_email(user_data.email)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is registerd",
            )

        new_user = User(
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            firstname=user_data.firstname,
            lastname=user_data.lastname,
            role=UserRole.USER,
            is_active=True,
            is_verified=False,
        )

        created_user = await self.user_repo.create(new_user)
        logger.info(
            "registration_succeeded",
            event="auth.registered",
            user_id=str(created_user.id),
        )
        return created_user

    async def admin_update_user(self, user_id: UUID, user_in: UserAdminUpdate) -> User:
        user = await self.get_user_by_id(user_id)
        return await self.user_repo.update_profile(user, user_in)

    async def update_my_profile(
        self, user_id: UUID, user_in: UserProfileUpdate
    ) -> User:
        user = await self.get_user_by_id(user_id)
        return await self.user_repo.update_profile(user, user_in)

    async def delete_user(self, user_id: UUID) -> None:
        user = await self.get_user_by_id(user_id)
        try:
            await self.user_repo.delete(user)
        except IntegrityError as exc:
            integrity_conflict(exc)

    async def get_users(self, params: PaginationParams) -> PaginateResponse:
        users, total = await self.user_repo.get_all(
            skip=params.offset, limit=params.limit
        )

        user_schema = [UserReponse.model_validate(u) for u in users]

        return PaginateResponse[UserReponse](
            items=user_schema, total=total, limit=params.limit, offset=params.offset
        )

    async def get_user_by_id(self, user_id: UUID) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return user
