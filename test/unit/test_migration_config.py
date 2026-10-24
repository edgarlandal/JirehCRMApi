from pathlib import Path
from runpy import run_path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.engine import make_url

from app.core.config import Setting


@pytest.mark.parametrize("host,port", [("postgres", "5432"), ("localhost", "5433")])
def test_database_urls_share_connection_settings(host, port):
    settings = Setting(
        _env_file=None,
        DB_HOST=host,
        DB_PORT=port,
        DB_USER="test",
        DB_PASSWORD="p@ss:/%word",
        DB_NAME="joblist_test",
        JWT_SECRET_KEY="test-only-secret-key-with-at-least-32-characters",
    )
    async_url = make_url(settings.database_url)
    sync_url = settings.migration_database_url
    assert async_url.drivername == "postgresql+asyncpg"
    assert sync_url.drivername == "postgresql+psycopg2"
    assert sync_url == async_url.set(drivername="postgresql+psycopg2")
    assert sync_url.host == host
    assert sync_url.port == int(port)
    assert sync_url.password == "p@ss:/%word"


@pytest.mark.parametrize("offline", [True, False])
def test_alembic_uses_application_settings(offline):
    from app.core.config import settings
    from app.core.database import Base

    config = MagicMock(config_file_name=None)
    config.get_main_option.return_value = "postgresql://wrong-host/unused"
    with (
        patch("alembic.context.config", config, create=True),
        patch("alembic.context.is_offline_mode", return_value=offline),
        patch("alembic.context.configure") as configure,
        patch("alembic.context.begin_transaction"),
        patch("alembic.context.run_migrations") as run,
        patch("sqlalchemy.create_engine") as engine,
    ):
        run_path(str(Path(__file__).resolve().parents[2] / "migrations" / "env.py"))
    if offline:
        assert configure.call_args.kwargs["url"] == settings.migration_database_url
        engine.assert_not_called()
    else:
        assert engine.call_args.args[0] == settings.migration_database_url
    run.assert_called_once()
    assert "refresh_token" in Base.metadata.tables
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
