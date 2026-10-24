from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_pagination(
        self, query: Select, limit: int = 20, offset: int = 0
    ) -> tuple[list[ModelType], int]:
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        paginated_qquery = query.offset(offset).limit(limit)
        items_result = await self.session.execute(paginated_qquery)
        items = items_result.scalars().all()

        return list(items), total
