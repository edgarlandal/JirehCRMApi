from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserProfileUpdate


class UserRepository:
    def __init__(self, db: AsyncSession) -> User | None:
        self.db = db

    async def create(self, user: User) -> User:
        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def update_profile(self, db_user: User, user_in: UserProfileUpdate) -> User:
        update_data = user_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_user, field, value)

        return await self.save(db_user)

    async def save(self, db_user: User) -> User:
        try:
            self.db.add(db_user)
            await self.db.commit()
            await self.db.refresh(db_user)
            return db_user
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def delete(self, db_user: User) -> None:
        try:
            await self.db.delete(db_user)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_by_email(self, email: UUID) -> User | None:
        try:
            res = await self.db.execute(select(User).where(User.email == email))
            return res.scalar_one_or_none()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_by_id(self, user_id: UUID) -> User | None:
        try:
            res = await self.db.execute(select(User).where(User.id == UUID(user_id)))
            return res.scalars().first()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_all(self, skip: int, limit: int) -> tuple[Sequence[User], int]:
        total = await self.db.scalar(select(func.count()).select_from(User))
        stmt = select(User).order_by(User.created_at, User.id).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return res.scalars().all(), total
