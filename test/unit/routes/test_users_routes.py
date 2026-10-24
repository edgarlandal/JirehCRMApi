"""Isolated HTTP tests for registration and the current user's profile."""

import pytest
from fastapi import HTTPException

from app.models.user import UserRole
from app.schemas.user import UserCreate, UserProfileUpdate


@pytest.fixture(autouse=True)
def normal_user(route_context):
    route_context.actor.role = UserRole.USER


async def test_register_without_authentication(route_client, route_context, user_payload):
    route_client.headers.pop("Authorization")
    response = await route_client.post("/api/v1/users", json=user_payload)
    assert response.status_code == 201
    assert response.json()["email"] == user_payload["email"]
    assert "password" not in response.json()
    assert "hashed_password" not in response.json()
    route_context.user_service.register_user.assert_awaited_once_with(UserCreate(**user_payload))


async def test_get_own_profile(route_client, route_context):
    response = await route_client.get("/api/v1/users/me")
    assert response.status_code == 200
    assert response.json()["id"] == str(route_context.actor.id)
    assert "hashed_password" not in response.json()
    assert route_context.user_service.mock_calls == []


async def test_update_own_profile(route_client, route_context):
    route_context.actor.firstname = "Updated"
    route_context.user_service.update_my_profile.return_value = route_context.actor
    response = await route_client.patch("/api/v1/users/me", json={"firstname": " Updated "})
    assert response.status_code == 200
    assert response.json()["firstname"] == "Updated"
    route_context.user_service.update_my_profile.assert_awaited_once_with(
        user_id=route_context.actor.id, user_in=UserProfileUpdate(firstname="Updated")
    )
    submitted = route_context.user_service.update_my_profile.await_args.kwargs["user_in"]
    assert submitted.model_dump(exclude_unset=True) == {"firstname": "Updated"}


async def test_delete_own_profile(route_client, route_context):
    response = await route_client.delete("/api/v1/users/me")
    assert response.status_code == 204
    assert response.content == b""
    route_context.user_service.get_user_by_id.assert_awaited_once_with(route_context.actor.id)
    route_context.user_service.delete_user.assert_awaited_once_with(route_context.actor.id)


async def test_missing_profile_stops_delete(route_client, route_context):
    route_context.user_service.get_user_by_id.side_effect = HTTPException(404, "User not found")
    response = await route_client.delete("/api/v1/users/me")
    assert response.status_code == 404
    route_context.user_service.delete_user.assert_not_awaited()


@pytest.mark.parametrize("payload", [
    {"role": "admin"}, {"is_active": False}, {"is_verified": True},
    {"firstname": None}, {"lastname": " "}, {"email": "other@example.com"},
])
async def test_profile_rejects_invalid_or_privileged_fields(route_client, route_context, payload):
    response = await route_client.patch("/api/v1/users/me", json=payload)
    assert response.status_code == 422
    route_context.user_service.update_my_profile.assert_not_awaited()


@pytest.mark.parametrize("path", ["/api/v1/users", "/api/v1/admin"])
@pytest.mark.parametrize("invalid", [{"email": "invalid"}, {"password": "weak"}, {"firstname": " "}])
async def test_registration_validation(route_client, route_context, user_payload, path, invalid):
    route_context.actor.role = UserRole.ADMIN
    response = await route_client.post(path, json={**user_payload, **invalid})
    assert response.status_code == 422
    route_context.user_service.register_user.assert_not_awaited()
