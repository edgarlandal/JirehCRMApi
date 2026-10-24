from app.core.security import verify_password


async def test_get_paginated(client, admin_token, test_user):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.get("/api/v1/admin?limit=5&offset=1", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["limit"] == 5
    assert data["offset"] == 1
    assert len(data["items"]) == 1
    first = await client.get("/api/v1/admin?limit=1&offset=0", headers=headers)
    assert first.status_code == 200
    assert first.json()["items"][0]["id"] != data["items"][0]["id"]
    empty = await client.get("/api/v1/admin?offset=2", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert empty.json()["total"] == 2


async def test_update_user_crud(client, admin_token, test_user, db_session):
    response = await client.patch(f"/api/v1/admin/{test_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"firstname": "Updated", "lastname": "Name"})
    assert response.status_code == 200
    assert response.json()["firstname"] == "Updated"
    assert response.json()["lastname"] == "Name"
    await db_session.refresh(test_user)
    assert test_user.firstname == "Updated"
    assert verify_password("Password123!", test_user.hashed_password)
