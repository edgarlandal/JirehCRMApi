from app.core.database import Base
from app.main import create_app


def test_api_registers_existing_and_crm_endpoints():
    app = create_app()
    registered = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/api/v1/")
        for method in operations
    }

    expected = {
        ("POST", "/api/v1/auth/register"),
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/logout"),
        ("POST", "/api/v1/auth/refresh"),
        ("POST", "/api/v1/users"),
        ("GET", "/api/v1/users/me"),
        ("PATCH", "/api/v1/users/me"),
        ("DELETE", "/api/v1/users/me"),
        ("POST", "/api/v1/admin"),
        ("GET", "/api/v1/admin"),
        ("GET", "/api/v1/admin/{user_id}"),
        ("PATCH", "/api/v1/admin/{user_id}"),
        ("DELETE", "/api/v1/admin/{user_id}"),
        ("GET", "/api/v1/health"),
        ("GET", "/api/v1/health/ready"),
    }
    for resource, identifier in (
        ("customers", "customer_id"),
        ("contacts", "contact_id"),
        ("services", "service_id"),
        ("interactions", "interaction_id"),
        ("appointments", "appointment_id"),
        ("tickets", "ticket_id"),
        ("ticket-comments", "comment_id"),
    ):
        root = f"/api/v1/{resource}"
        expected.update(
            {
                ("POST", root),
                ("GET", root),
                ("GET", f"{root}/{{{identifier}}}"),
                ("PATCH", f"{root}/{{{identifier}}}"),
            }
        )
    expected.update(
        {
            ("POST", "/api/v1/customers/{customer_id}/archive"),
            ("POST", "/api/v1/contacts/{contact_id}/deactivate"),
            ("POST", "/api/v1/services/{service_id}/deactivate"),
        }
    )
    assert registered == expected


def test_metadata_contains_auth_and_crm():
    assert set(Base.metadata.tables) == {
        "users",
        "refresh_token",
        "customers",
        "contacts",
        "services",
        "interactions",
        "appointments",
        "tickets",
        "ticket_comments",
    }
