"""Verify CRM migrations and business tests in a disposable PostgreSQL database.

Run from the repository root: python -m scripts.verify_crm_migration
Uses the configured PostgreSQL server/user, but never migrates the app database.
The database role must have CREATEDB permission. Requires requirements-dev.txt.
"""

import os
import subprocess
import sys
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.core.config import settings

INITIAL = "9f2a3c6d8e41"
CRM_HEAD = "c7a1e4b92063"
CRM_ENUMS = {
    "crm_customer_type_enum",
    "crm_customer_status_enum",
    "crm_interaction_channel_enum",
    "crm_appointment_status_enum",
    "crm_ticket_status_enum",
    "crm_ticket_priority_enum",
}
CRM_TABLES = {
    "customers",
    "contacts",
    "services",
    "interactions",
    "appointments",
    "tickets",
    "ticket_comments",
}


def verify() -> None:
    database_name = f"crm_verify_{uuid4().hex}"
    original_database = settings.DB_NAME
    admin_engine = create_engine(
        settings.migration_database_url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        hide_parameters=True,
    )
    test_engine = None
    created = False
    try:
        with admin_engine.connect() as conn:
            # Name is generated here, contains only a fixed prefix and UUID hex.
            conn.execute(text(f'CREATE DATABASE "{database_name}"'))
        created = True
        settings.DB_NAME = database_name
        config = Config("alembic.ini")
        assert ScriptDirectory.from_config(config).get_heads() == [CRM_HEAD]
        command.upgrade(config, INITIAL)
        test_engine = create_engine(
            settings.migration_database_url, hide_parameters=True
        )
        user_id, token_id = uuid4(), str(uuid4())
        with test_engine.begin() as conn:
            conn.execute(
                text("""INSERT INTO users
                (id, email, hashed_password, firstname, lastname, role, is_active, is_verified, created_at, updated_at)
                VALUES (:id, 'migration@example.com', 'test-only', 'Before', 'Migration', 'ADMIN', true, true, now(), now())"""),
                {"id": user_id},
            )
            conn.execute(
                text("""INSERT INTO refresh_token
                (id, token_hash, user_email, family_id, revoked, expires_at, created_at)
                VALUES (:id, 'test-hash', 'migration@example.com', 'test-family', false, now() + interval '1 day', now())"""),
                {"id": token_id},
            )
            original_user = conn.execute(text("SELECT * FROM users")).mappings().one()
            original_token = (
                conn.execute(text("SELECT * FROM refresh_token")).mappings().one()
            )

        def assert_auth_unchanged():
            with test_engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT * FROM users")).mappings().one()
                    == original_user
                )
                assert (
                    conn.execute(text("SELECT * FROM refresh_token")).mappings().one()
                    == original_token
                )

        command.upgrade(config, "head")
        command.check(config)
        assert_auth_unchanged()
        inspector = inspect(test_engine)
        assert set(inspector.get_table_names()) == CRM_TABLES | {
            "users",
            "refresh_token",
            "alembic_version",
        }
        assert {item["name"] for item in inspector.get_enums()} == CRM_ENUMS | {
            "user_role_enum"
        }
        for table in CRM_TABLES:
            assert all(
                fk["options"].get("ondelete") == "RESTRICT"
                for fk in inspector.get_foreign_keys(table)
            )
        assert "ck_appointments_interval" in {
            item["name"] for item in inspector.get_check_constraints("appointments")
        }
        assert "ck_tickets_resolution" in {
            item["name"] for item in inspector.get_check_constraints("tickets")
        }
        command.downgrade(config, INITIAL)
        assert_auth_unchanged()
        inspector = inspect(test_engine)
        assert set(inspector.get_table_names()) == {
            "users",
            "refresh_token",
            "alembic_version",
        }
        assert {item["name"] for item in inspector.get_enums()} == {"user_role_enum"}
        command.upgrade(config, "head")
        command.check(config)
        assert_auth_unchanged()
        test_engine.dispose()
        env = os.environ.copy()
        env["CRM_TEST_DATABASE_URL"] = settings.database_url
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "test/integration/test_crm.py",
                "test/integration/test_crm_routes.py",
                "-q",
            ],
            env=env,
            check=True,
        )
        print(
            "PostgreSQL verified: upgrade/downgrade/upgrade, enums, constraints, preserved auth data, and CRM tests."
        )
    finally:
        settings.DB_NAME = original_database
        if test_engine is not None:
            test_engine.dispose()
        if created:
            with admin_engine.connect() as conn:
                conn.execute(text(f'DROP DATABASE "{database_name}"'))
        admin_engine.dispose()


if __name__ == "__main__":
    verify()
