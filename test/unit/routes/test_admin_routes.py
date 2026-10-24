"""Isolated HTTP tests for the admin router."""

import pytest
from fastapi import HTTPException

from app.schemas.pagination import PaginationParams
from app.schemas.user import UserAdminUpdate, UserCreate


async def test_create_user(route_client, route_context, user_payload):
    response = await route_client.post("/api/v1/admin", json=user_payload)
    assert response.status_code == 201
    assert response.json()["id"] == str(route_context.target.id)
    assert "hashed_password" not in response.json()
    assert "password" not in response.json()
    route_context.user_service.register_user.assert_awaited_once_with(UserCreate(**user_payload))


async def test_list_users(route_client, route_context):
    route_context.user_service.get_users.return_value = {
        "items": [route_context.target], "total": 8, "limit": 2, "offset": 3,
    }
    response = await route_client.get("/api/v1/admin?limit=2&offset=3")
    assert response.status_code == 200
    data = response.json()
    assert (data["total"], data["limit"], data["offset"]) == (8, 2, 3)
    assert data["items"][0]["id"] == str(route_context.target.id)
    assert "hashed_password" not in data["items"][0]
    route_context.user_service.get_users.assert_awaited_once_with(PaginationParams(limit=2, offset=3))


async def test_get_user(route_client, route_context):
    user_id = str(route_context.target.id)
    response = await route_client.get(f"/api/v1/admin/{user_id}")
    assert response.status_code == 200
    assert response.json()["id"] == user_id
    route_context.user_service.get_user_by_id.assert_awaited_once_with(user_id)


async def test_update_user(route_client, route_context):
    payload = {"firstname": "Updated", "role": "admin", "is_active": False, "is_verified": True}
    for name, value in payload.items():
        setattr(route_context.target, name, value)
    user_id = str(route_context.target.id)
    response = await route_client.patch(f"/api/v1/admin/{user_id}", json=payload)
    assert response.status_code == 200
    assert all(response.json()[name] == value for name, value in payload.items())
    route_context.user_service.admin_update_user.assert_awaited_once_with(
        user_id=user_id, user_in=UserAdminUpdate(**payload)
    )


async def test_delete_user(route_client, route_context):
    user_id = str(route_context.target.id)
    response = await route_client.delete(f"/api/v1/admin/{user_id}")
    assert response.status_code == 204
    assert response.content == b""
    route_context.user_service.delete_user.assert_awaited_once_with(user_id)


@pytest.mark.parametrize("method,service_method", [
    ("GET", "get_user_by_id"), ("PATCH", "admin_update_user"), ("DELETE", "delete_user"),
])
async def test_user_not_found(route_client, route_context, method, service_method):
    getattr(route_context.user_service, service_method).side_effect = HTTPException(404, "User not found")
    kwargs = {"json": {"firstname": "Updated"}} if method == "PATCH" else {}
    response = await route_client.request(method, f"/api/v1/admin/{route_context.target.id}", **kwargs)
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
async def test_invalid_uuid_does_not_call_service(route_client, route_context, method):
    kwargs = {"json": {}} if method == "PATCH" else {}
    response = await route_client.request(method, "/api/v1/admin/not-a-uuid", **kwargs)
    assert response.status_code == 422
    assert route_context.user_service.mock_calls == []


@pytest.mark.parametrize("payload", [
    {"role": "owner"}, {"role": None}, {"is_active": None}, {"is_verified": None},
    {"firstname": " "}, {"password": "Changed123!"},
])
async def test_invalid_update_does_not_call_service(route_client, route_context, payload):
    response = await route_client.patch(f"/api/v1/admin/{route_context.target.id}", json=payload)
    assert response.status_code == 422
    route_context.user_service.admin_update_user.assert_not_awaited()


async def test_duplicate_email_error(route_client, route_context, user_payload):
    route_context.user_service.register_user.side_effect = HTTPException(400, "Email is registerd")
    response = await route_client.post("/api/v1/admin", json=user_payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email is registerd"
