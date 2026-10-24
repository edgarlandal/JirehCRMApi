from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, user_email: str, token_hash: str, family_id: str, expires_at: datetime
    ) -> RefreshToken:
        db_token = RefreshToken(
            user_email=user_email,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
        )
        self.db.add(db_token)
        await self.db.commit()
        await self.db.refresh(db_token)

        return db_token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def mark_as_used(self, token_id: str):
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(used_at=datetime.now(timezone.utc), revoked=True)
        )

        await self.db.commit()

    async def revoke(self, token_hash: str) -> bool:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(revoked=True)
        )

        await self.db.execute(stmt)
        await self.db.commit()
        return True

    async def revoke_family(self, family_id: str):
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id)
            .values(revoked=True)
        )

        await self.db.commit()
