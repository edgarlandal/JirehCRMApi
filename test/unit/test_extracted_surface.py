from app.core.database import Base
from app.main import create_app


def test_api_registers_only_retained_endpoints():
    app = create_app()
    registered = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/api/v1/")
        for method in operations
    }

    assert registered == {
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


def test_metadata_contains_only_users_and_refresh_tokens():
    assert set(Base.metadata.tables) == {"users", "refresh_token"}
