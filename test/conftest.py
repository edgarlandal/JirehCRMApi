import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Test configuration must never connect to the application's database or Redis.
for key, value in {
    "DB_HOST": "127.0.0.1", "DB_PORT": "5432", "DB_NAME": "joblist_test",
    "DB_USER": "test", "DB_PASSWORD": "test",
    "JWT_SECRET_KEY": "test-only-secret-key-with-at-least-32-characters",
    "REDIS_URL": "memory://", "DEBUG": "false",
}.items():
    os.environ[key] = value

from app.api.dependencies import get_async_db
from app.core.database import Base
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.models.user import User, UserRole


@pytest_asyncio.fixture
async def engine_test():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine_test) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine_test, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    app.state.limiter.reset()

    async def override_db():
        yield db_session

    app.dependency_overrides[get_async_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
        app.state.limiter.reset()


@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(email="test@example.com", hashed_password=hash_password("Password123!"),
                firstname="Test", lastname="User", role=UserRole.USER, is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session):
    user = User(email="admin@example.com", hashed_password=hash_password("AdminPassword123!"),
                firstname="Admin", lastname="User", role=UserRole.ADMIN, is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def disabled_user(test_user, db_session):
    test_user.is_active = False
    await db_session.commit()
    return test_user


@pytest.fixture
def user_token(test_user):
    return create_access_token(data={"sub": test_user.email})


@pytest.fixture
def admin_token(admin_user):
    return create_access_token(data={"sub": admin_user.email})


@pytest_asyncio.fixture
async def refresh_token_string(client, test_user):
    response = await client.post("/api/v1/auth/login", data={
        "username": test_user.email, "password": "Password123!"})
    assert response.status_code == 200
    return response.json()["refresh_token"]
