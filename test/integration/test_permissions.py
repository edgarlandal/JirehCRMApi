async def test_user_cannot_access_admin_endpoint(client, user_token):
    response = await client.get("/api/v1/admin", headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 403


async def test_admin_can_access_admin_endpoint(client, admin_token):
    response = await client.get("/api/v1/admin", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json()["total"] == 1


async def test_user_cannot_update_user(client, user_token, test_user):
    response = await client.patch(f"/api/v1/admin/{test_user.id}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"firstname": "Updated", "lastname": "User"})
    assert response.status_code == 403
