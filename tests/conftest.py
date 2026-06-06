import os

import psycopg2
import pytest

os.environ["DATABASE_URL"] = "postgresql://talentforge:talentforge123@localhost:5432/talentforge_test"
os.environ["PGSSLMODE"] = "disable"


def pytest_sessionstart(session):
    session.config._pg_available = False
    try:
        conn = psycopg2.connect(
            "postgresql://talentforge:talentforge123@localhost:5432/talentforge_test"
        )
        conn.set_session(autocommit=True)
        cur = conn.cursor()
        cur.execute("DROP SCHEMA public CASCADE")
        cur.execute("CREATE SCHEMA public")
        cur.close()
        conn.close()
        session.config._pg_available = True
        print("[conftest] PostgreSQL test database reset: talentforge_test")
    except Exception as e:
        print(
            "[conftest] PostgreSQL test database unavailable; skipping schema reset. "
            f"Integration tests requiring DB will fail. Error: {e}"
        )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require PostgreSQL (deselect with '-m \"not integration\"')",
    )


def pytest_collection_modifyitems(config, items):
    if getattr(config, "_pg_available", False):
        return
    skip_db = pytest.mark.skip(reason="PostgreSQL test database not available")
    for item in items:
        if "test_proctoring" in item.module.__name__ or "test_api" in item.module.__name__:
            item.add_marker(skip_db)
