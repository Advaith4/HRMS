"""Initialize TalentForge tables against the configured DATABASE_URL."""

from src.database.connection import create_db_and_tables


if __name__ == "__main__":
    create_db_and_tables()
    print("TalentForge database schema initialized.")
