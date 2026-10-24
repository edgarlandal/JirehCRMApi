from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.security import verify_password
from app.models.user import User, UserRole


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def user_payload(**overrides):
    return {
        "email": "new@example.com",
        "password": "Password123!",
        "firstname": "New",
        "lastname": "User",
        **overrides,
    }


async def test_admin_create_and_read_user(client, admin_headers, db_session):
    response = await client.post(
        "/api/v1/admin", headers=admin_headers, json=user_payload()
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert data["is_verified"] is False
    assert "password" not in data
    assert "hashed_password" not in data
    user = await db_session.scalar(select(User).where(User.email == data["email"]))
    assert verify_password("Password123!", user.hashed_password)
    response = await client.get(f"/api/v1/admin/{data['id']}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == data


async def test_admin_create_duplicate_email(client, admin_headers, test_user):
    response = await client.post(
        "/api/v1/admin", headers=admin_headers,
        json=user_payload(email=test_user.email),
    )
    assert response.status_code == 400


@pytest.mark.parametrize("payload", [
    {"email": "invalid"}, {"password": "weak"}, {"firstname": " "},
])
async def test_admin_create_validates_user(client, admin_headers, payload):
    response = await client.post(
        "/api/v1/admin", headers=admin_headers, json=user_payload(**payload)
    )
    assert response.status_code == 422


async def test_admin_update_fields(client, admin_headers, test_user, db_session):
    response = await client.patch(
        f"/api/v1/admin/{test_user.id}", headers=admin_headers,
        json={"firstname": " Updated ", "role": "admin",
              "is_active": False, "is_verified": True},
    )
    assert response.status_code == 200
    await db_session.refresh(test_user)
    assert test_user.firstname == "Updated"
    assert test_user.lastname == "User"
    assert test_user.role == UserRole.ADMIN
    assert test_user.is_active is False
    assert test_user.is_verified is True
    assert verify_password("Password123!", test_user.hashed_password)
    response = await client.patch(
        f"/api/v1/admin/{test_user.id}", headers=admin_headers,
        json={"role": "user", "is_active": True, "is_verified": False},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "user"
    assert response.json()["is_active"] is True
    assert response.json()["is_verified"] is False


@pytest.mark.parametrize("payload", [
    {"firstname": None}, {"lastname": None}, {"role": None},
    {"is_active": None}, {"is_verified": None}, {"role": "owner"},
    {"firstname": " "}, {"lastname": ""},
    {"password": "ChangedPassword123!"}, {"email": "changed@example.com"},
])
async def test_admin_update_rejects_invalid_fields(
    client, admin_headers, test_user, db_session, payload
):
    response = await client.patch(
        f"/api/v1/admin/{test_user.id}", headers=admin_headers, json=payload
    )
    assert response.status_code == 422
    await db_session.refresh(test_user)
    assert test_user.firstname == "Test"
    assert test_user.role == UserRole.USER
    assert test_user.is_active is True


async def test_admin_empty_patch_preserves_user(client, admin_headers, test_user):
    path = f"/api/v1/admin/{test_user.id}"
    before = await client.get(path, headers=admin_headers)
    response = await client.patch(path, headers=admin_headers, json={})
    assert response.status_code == 200
    assert response.json() == before.json()


async def test_admin_delete_user(client, admin_headers, test_user):
    path = f"/api/v1/admin/{test_user.id}"
    response = await client.delete(path, headers=admin_headers)
    assert response.status_code == 204
    assert response.content == b""
    response = await client.get(path, headers=admin_headers)
    assert response.status_code == 404


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
@pytest.mark.parametrize("user_id,expected", [("invalid", 422), (str(uuid4()), 404)])
async def test_admin_invalid_or_missing_user(client, admin_headers, method, user_id, expected):
    kwargs = {"json": {"firstname": "Updated"}} if method == "PATCH" else {}
    response = await client.request(
        method, f"/api/v1/admin/{user_id}", headers=admin_headers, **kwargs
    )
    assert response.status_code == expected


@pytest.mark.parametrize("method,path,payload", [
    ("GET", "", None), ("POST", "", user_payload()),
    ("GET", "/{id}", None), ("PATCH", "/{id}", {"role": "admin"}),
    ("DELETE", "/{id}", None),
])
@pytest.mark.parametrize("authenticated", [False, True])
async def test_admin_requires_admin_role(
    client, test_user, user_token, method, path, payload, authenticated
):
    headers = {"Authorization": f"Bearer {user_token}"} if authenticated else {}
    kwargs = {"json": payload} if payload is not None else {}
    response = await client.request(
        method, "/api/v1/admin" + path.format(id=test_user.id), headers=headers, **kwargs
    )
    assert response.status_code == (403 if authenticated else 401)


async def test_disabled_admin_cannot_list_users(client, admin_headers, admin_user, db_session):
    admin_user.is_active = False
    await db_session.commit()
    response = await client.get("/api/v1/admin", headers=admin_headers)
    assert response.status_code == 400


@pytest.mark.parametrize("payload", [
    {"role": "admin"}, {"is_active": False}, {"is_verified": True},
])
async def test_normal_profile_rejects_admin_fields(client, user_token, test_user, payload):
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await client.patch("/api/v1/users/me", headers=headers, json=payload)
    assert response.status_code == 422
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "user"
    assert response.json()["is_active"] is True
    assert response.json()["is_verified"] is False
