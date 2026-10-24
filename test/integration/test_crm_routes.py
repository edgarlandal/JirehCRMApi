from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio

from app.core.security import create_access_token
from app.main import create_app

RESOURCES = (
    "customers",
    "contacts",
    "services",
    "interactions",
    "appointments",
    "tickets",
    "ticket-comments",
)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def api_crm(client, user_token, admin_token, test_user):
    async def create(resource, payload, token=user_token):
        response = await client.post(
            f"/api/v1/{resource}", json=payload, headers=auth(token)
        )
        assert response.status_code == 201, response.text
        return response.json()

    customer = await create("customers", {"name": "ACME", "customer_type": "COMPANY"})
    contact = await create(
        "contacts",
        {"customer_id": customer["id"], "firstname": "Ana", "email": "ana@example.com"},
    )
    catalog_service = await create("services", {"name": "Support"}, admin_token)
    ticket = await create(
        "tickets",
        {
            "customer_id": customer["id"],
            "contact_id": contact["id"],
            "service_id": catalog_service["id"],
            "subject": "Connection",
            "description": "Offline",
        },
    )
    now = datetime.now(timezone.utc)
    interaction = await create(
        "interactions",
        {
            "customer_id": customer["id"],
            "contact_id": contact["id"],
            "channel": "CALL",
            "summary": "First call",
            "occurred_at": now.isoformat(),
        },
    )
    appointment = await create(
        "appointments",
        {
            "customer_id": customer["id"],
            "contact_id": contact["id"],
            "assigned_to_id": str(test_user.id),
            "title": "Diagnosis",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(hours=1)).isoformat(),
            "meeting_url": "https://example.com/meeting",
        },
    )
    comment = await create(
        "ticket-comments", {"ticket_id": ticket["id"], "body": "Investigating"}
    )
    return dict(
        zip(
            RESOURCES,
            (
                customer,
                contact,
                catalog_service,
                interaction,
                appointment,
                ticket,
                comment,
            ),
        )
    )


@pytest.mark.parametrize(
    "resource,patch",
    [
        ("customers", {"name": "Updated"}),
        ("contacts", {"email": None, "is_active": False}),
        ("services", {"is_active": False}),
        ("interactions", {"summary": "Updated"}),
        ("appointments", {"meeting_url": None}),
        ("tickets", {"priority": "HIGH"}),
        ("ticket-comments", {"is_internal": False}),
    ],
)
async def test_crm_http_create_read_list_patch(
    client, api_crm, user_token, admin_token, test_user, resource, patch
):
    record = api_crm[resource]
    token = admin_token if resource == "services" else user_token
    path = f"/api/v1/{resource}/{record['id']}"
    response = await client.get(path, headers=auth(user_token))
    assert response.status_code == 200
    assert response.json() == record
    assert "hashed_password" not in response.text
    creator = "author_user_id" if resource == "ticket-comments" else "created_by_id"
    if creator in record:
        assert record[creator] == str(test_user.id)
    response = await client.get(
        f"/api/v1/{resource}", params={"limit": 1}, headers=auth(user_token)
    )
    assert response.status_code == 200
    assert response.json() == {"items": [record], "total": 1, "limit": 1, "offset": 0}
    response = await client.patch(path, json=patch, headers=auth(token))
    assert response.status_code == 200, response.text
    for key, value in patch.items():
        assert response.json()[key] == value


@pytest.mark.parametrize("resource", RESOURCES)
async def test_all_crm_routes_require_authentication(client, resource):
    root = f"/api/v1/{resource}"
    for method, path, payload in (
        ("GET", root, None),
        ("POST", root, {}),
        ("GET", f"{root}/{uuid4()}", None),
        ("PATCH", f"{root}/{uuid4()}", {}),
    ):
        response = await client.request(method, path, json=payload)
        assert response.status_code == 401


@pytest.mark.parametrize("resource", RESOURCES)
async def test_inactive_users_cannot_access_crm(client, disabled_user, resource):
    token = create_access_token({"sub": disabled_user.email})
    response = await client.get(f"/api/v1/{resource}", headers=auth(token))
    assert response.status_code == 400


@pytest.mark.parametrize("resource", RESOURCES)
async def test_query_validation_returns_422(client, user_token, resource):
    for params in (
        {"limit": 101},
        {"offset": -1},
        {"unexpected": "value"},
        {
            "created_from": "2026-10-25T00:00:00Z",
            "created_until": "2026-10-24T00:00:00Z",
        },
        {"created_from": "2026-10-24T12:00:00"},
    ):
        response = await client.get(
            f"/api/v1/{resource}", params=params, headers=auth(user_token)
        )
        assert response.status_code == 422, response.text
    response = await client.get(
        f"/api/v1/{resource}/invalid-uuid", headers=auth(user_token)
    )
    assert response.status_code == 422
    response = await client.get(
        f"/api/v1/{resource}/{uuid4()}", headers=auth(user_token)
    )
    assert response.status_code == 404


async def test_customer_scope_applies_to_all_http_resources(
    client, api_crm, user_token, admin_token, admin_user
):
    customer_id = api_crm["customers"]["id"]
    response = await client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"assigned_to_id": str(admin_user.id)},
        headers=auth(user_token),
    )
    assert response.status_code == 403
    response = await client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"assigned_to_id": str(admin_user.id)},
        headers=auth(admin_token),
    )
    assert response.status_code == 200
    for resource in RESOURCES:
        if resource == "services":
            continue
        path = f"/api/v1/{resource}/{api_crm[resource]['id']}"
        assert (await client.get(path, headers=auth(user_token))).status_code == 404
        assert (
            await client.patch(path, json={}, headers=auth(user_token))
        ).status_code == 404
        response = await client.get(f"/api/v1/{resource}", headers=auth(user_token))
        assert response.json()["total"] == 0
        assert (await client.get(path, headers=auth(admin_token))).status_code == 200
    response = await client.get(
        "/api/v1/ticket-comments",
        params={"ticket_id": api_crm["tickets"]["id"]},
        headers=auth(user_token),
    )
    assert response.status_code == 404
    response = await client.post(
        "/api/v1/ticket-comments",
        json={"ticket_id": api_crm["tickets"]["id"], "body": "Forbidden"},
        headers=auth(user_token),
    )
    assert response.status_code == 404


async def test_catalog_admin_permission_and_archive_actions(
    client, api_crm, user_token, admin_token
):
    root = f"/api/v1/services/{api_crm['services']['id']}"
    for method, path, data in (
        ("POST", "/api/v1/services", {"name": "Forbidden"}),
        ("PATCH", root, {"name": "Forbidden"}),
        ("POST", root + "/deactivate", None),
    ):
        response = await client.request(
            method, path, json=data, headers=auth(user_token)
        )
        assert response.status_code == 403
    for resource, action, key, value, token in (
        ("customers", "archive", "status", "INACTIVE", user_token),
        ("contacts", "deactivate", "is_active", False, user_token),
        ("services", "deactivate", "is_active", False, admin_token),
    ):
        path = f"/api/v1/{resource}/{api_crm[resource]['id']}/{action}"
        assert (await client.post(path)).status_code == 401
        response = await client.post(path, headers=auth(token))
        assert response.status_code == 200
        assert response.json()[key] == value
    response = await client.get(
        "/api/v1/services", params={"is_active": "false"}, headers=auth(user_token)
    )
    assert response.json()["total"] == 1
    response = await client.get(
        "/api/v1/ticket-comments",
        params={"ticket_id": api_crm["tickets"]["id"]},
        headers=auth(user_token),
    )
    assert response.json()["items"][0]["id"] == api_crm["ticket-comments"]["id"]


async def test_http_business_rules_and_internal_fields(client, api_crm, user_token):
    headers = auth(user_token)
    ticket = api_crm["tickets"]
    path = f"/api/v1/tickets/{ticket['id']}"
    for payload in (
        {"created_by_id": str(uuid4())},
        {"resolved_at": None},
        {"subject": None},
        {"subject": " "},
    ):
        assert (
            await client.patch(path, json=payload, headers=headers)
        ).status_code == 422
    assert (
        await client.patch(path, json={"status": "CLOSED"}, headers=headers)
    ).status_code == 409
    for target in ("RESOLVED", "CLOSED", "OPEN"):
        response = await client.patch(path, json={"status": target}, headers=headers)
        assert response.status_code == 200
        assert (response.json()["resolved_at"] is not None) == (target != "OPEN")
        assert (response.json()["closed_at"] is not None) == (target == "CLOSED")
    response = await client.post(
        "/api/v1/customers",
        json={"name": "Other", "customer_type": "PERSON"},
        headers=headers,
    )
    other_id = response.json()["id"]
    response = await client.post(
        "/api/v1/contacts",
        json={"customer_id": other_id, "firstname": "Other"},
        headers=headers,
    )
    assert (
        await client.patch(
            path, json={"contact_id": response.json()["id"]}, headers=headers
        )
    ).status_code == 422
    appointment = api_crm["appointments"]
    response = await client.patch(
        f"/api/v1/appointments/{appointment['id']}",
        json={"ends_at": appointment["starts_at"]},
        headers=headers,
    )
    assert response.status_code == 422


def test_openapi_documents_crm_auth_filters_and_responses():
    schema = create_app().openapi()
    for resource in RESOURCES:
        path = schema["paths"][f"/api/v1/{resource}"]
        assert "201" in path["post"]["responses"]
        assert "requestBody" not in path["get"]
        assert {"limit", "offset", "created_from", "created_until"} <= {
            parameter["name"] for parameter in path["get"]["parameters"]
        }
        for operation in path.values():
            assert operation["security"] == [{"OAuth2PasswordBearer": []}]
