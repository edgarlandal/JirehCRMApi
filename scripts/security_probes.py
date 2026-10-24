"""Historical security probes assert observed vulnerabilities; not a release gate."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "test"))
import conftest  # Configure isolated test environment before app imports.

pytest_plugins = ["conftest"]

from app.core.config import settings
from app.core.security import (
    create_refresh_token,
    decode_acces_token,
    hash_password,
    verify_password,
)
from app.schemas.user import UserProfileUpdate


def test_argon2id_hash_and_wrong_password():
    encoded = hash_password("AuditPassword123!")
    assert encoded.startswith("$argon2id$")
    assert verify_password("AuditPassword123!", encoded)
    assert not verify_password("wrong", encoded)


def test_wrong_signature_rejected():
    token = jwt.encode(
        {"sub": "audit@example.com", "type": "access"},
        "different-audit-secret-at-least-32-characters",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as error:
        decode_acces_token(token, "access")
    assert error.value.status_code == 401


def test_observed_signed_token_without_exp_accepted():
    token = jwt.encode(
        {"sub": "audit@example.com", "type": "access"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert decode_acces_token(token, "access")["sub"] == "audit@example.com"


def test_observed_refresh_token_collision_in_same_second():
    with patch("app.core.security.datetime") as clock:
        clock.now.return_value = datetime(2026, 9, 10, tzinfo=timezone.utc)
        first = create_refresh_token(
            {"sub": "audit@example.com", "family_id": "same-session"}
        )
        second = create_refresh_token(
            {"sub": "audit@example.com", "family_id": "same-session"}
        )
    assert first == second


def test_observed_update_accepts_weak_password():
    data = UserProfileUpdate(firstname="Audit", lastname="User", password="x")
    assert data.password == "x"


async def test_observed_user_reads_another_users_profile(
    client, user_token, admin_user
):
    response = await client.get(
        f"/api/v1/users/{admin_user.id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == admin_user.email


async def test_observed_patch_cors_preflight_denied(client):
    response = await client.options(
        "/api/v1/users/example",
        headers={
            "Origin": settings.ALLOWED_ORIGINS[0],
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 400


async def test_observed_login_limit_bypassed_with_forwarded_for(client):
    body = {"username": "absent@example.com", "password": "wrong"}
    for _ in range(5):
        response = await client.post("/api/v1/auth/login", data=body)
        assert response.status_code == 400
    assert (await client.post("/api/v1/auth/login", data=body)).status_code == 429
    bypass = await client.post(
        "/api/v1/auth/login", data=body, headers={"X-Forwarded-For": "198.51.100.22"}
    )
    assert bypass.status_code == 400


async def test_observed_access_valid_after_logout(client, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.email, "password": "Password123!"},
    )
    assert response.status_code == 200
    tokens = response.json()
    assert (
        await client.post(
            "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
        )
    ).status_code == 200
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200


async def test_observed_production_healthcheck_path_missing(client):
    assert (await client.get("/health/liveness")).status_code == 404
    assert (await client.get("/api/v1/health")).status_code == 200


async def test_security_headers_and_sql_injection_probe(client):
    response = await client.post(
        "/api/v1/auth/login", data={"username": "' OR 1=1 --", "password": "wrong"}
    )
    assert response.status_code == 400
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "set-cookie" not in response.headers


def test_observed_database_url_password_not_redacted():
    from app.core.logging_config import redact_sensitive_data

    message = "Database error postgresql://audit:synthetic-audit-password@db/test"
    assert "synthetic-audit-password" in redact_sensitive_data(message)


async def test_observed_invalid_uuid_returns_generic_500_without_security_headers(
    client, user_token
):
    client._transport.raise_app_exceptions = False
    response = await client.get(
        "/api/v1/users/not-a-uuid", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 500
    assert (
        response.json()["message"]
        == "There was an internal error processing the request."
    )
    assert "x-request-id" in response.headers
    assert "x-frame-options" not in response.headers


async def test_observed_undecorated_route_not_limited(client):
    for _ in range(101):
        assert (await client.get("/api/v1/health")).status_code == 200
