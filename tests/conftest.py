import os
import psycopg2

os.environ["DATABASE_URL"] = "postgresql://talentforge:talentforge123@localhost:5432/talentforge_test"
os.environ["PGSSLMODE"] = "disable"


def pytest_sessionstart(session):
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
        print("[conftest] PostgreSQL test database reset: talentforge_test")
    except Exception as e:
        raise RuntimeError(
            f"PostgreSQL not available at postgresql://talentforge:talentforge123@localhost:5432/talentforge_test. "
            f"Ensure Docker PostgreSQL is running: docker compose up -d\n  Error: {e}"
        ) from e
