from datetime import timedelta

from app.core.security import create_jwt_token


async def test_register_user(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "new@example.com", "password": "Password123!",
        "firstname": "New", "lastname": "User"})
    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"
    assert response.json()["last_login_at"] is None
    assert "hashed_password" not in response.json()


async def test_expired_jwt_token(client, test_user):
    expired_token = create_jwt_token(
        data={"sub": test_user.email}, expire_data=timedelta(seconds=-1), token_type="access")
    response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Token expired"


async def test_logout(client, user_token, refresh_token_string):
    response = await client.post("/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"refresh_token": refresh_token_string})
    assert response.status_code == 200
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_string})
    assert response.status_code == 401


async def test_login_disabled_user(client, disabled_user):
    response = await client.post("/api/v1/auth/login",
        data={"username": disabled_user.email, "password": "Password123!"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive user account"


async def test_login_and_get_profile(client, test_user):
    response = await client.post("/api/v1/auth/login",
        data={"username": test_user.email, "password": "Password123!"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["id"] == str(test_user.id)
