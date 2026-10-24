import pytest
from sqlalchemy.exc import IntegrityError
from app.models.user import User


async def test_pydantic_validation_invalid_email(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "not-an-email", "password": "Password123!", "firstname": "Test", "lastname": "User"})
    assert response.status_code == 422
    assert any(error["field"] == "body -> email" for error in response.json()["details"])


async def test_duplicate_email_registration(client, test_user):
    response = await client.post("/api/v1/auth/register", json={
        "email": test_user.email, "password": "Password123!", "firstname": "Test", "lastname": "User"})
    assert response.status_code == 400
    assert "email" in response.json()["detail"].lower()


async def test_sql_unique_constraint_duplicate_email(db_session, test_user):
    db_session.add(User(email=test_user.email, hashed_password=test_user.hashed_password,
                        firstname="Duplicate", lastname="User"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
