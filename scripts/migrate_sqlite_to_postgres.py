"""Copy an existing TalentForge SQLite database into configured PostgreSQL."""

import argparse
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, func, inspect, select, text
from sqlmodel import SQLModel

from src.database.connection import create_db_and_tables, engine as target_engine


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="talentforge.db", help="Path to the source SQLite database.")
    return parser.parse_args()


def quote_identifier(value: str) -> str:
    return target_engine.dialect.identifier_preparer.quote(value)


if __name__ == "__main__":
    args = parse_args()
    source_path = Path(args.source).resolve()
    if not source_path.exists():
        raise SystemExit(f"SQLite source database not found: {source_path}")
    if target_engine.url.get_backend_name() != "postgresql":
        raise SystemExit("DATABASE_URL must point to Supabase PostgreSQL before running migration.")

    source_engine = create_engine(f"sqlite:///{source_path.as_posix()}")
    source_tables = set(inspect(source_engine).get_table_names())
    source_metadata = MetaData()
    create_db_and_tables()

    copied: dict[str, int] = {}
    with source_engine.connect() as source, target_engine.begin() as target:
        for table in SQLModel.metadata.sorted_tables:
            if table.name not in source_tables:
                continue
            existing = target.execute(select(func.count()).select_from(table)).scalar_one()
            if existing:
                raise SystemExit(f"Destination table is not empty: {table.name}")

            source_table = Table(table.name, source_metadata, autoload_with=source_engine)
            target_columns = set(table.c.keys())
            rows = [
                {
                    key: value
                    for key, value in dict(row._mapping).items()
                    if key in target_columns
                }
                for row in source.execute(select(source_table)).all()
            ]
            if rows:
                target.execute(table.insert(), rows)
            copied[table.name] = len(rows)

        for table in SQLModel.metadata.sorted_tables:
            integer_pk = next(
                (column for column in table.primary_key.columns if str(column.type).upper() == "INTEGER"),
                None,
            )
            if not integer_pk or table.name not in copied:
                continue
            table_name = quote_identifier(table.name)
            column_name = quote_identifier(integer_pk.name)
            target.execute(
                text(
                    "SELECT setval("
                    f"pg_get_serial_sequence('{table.name}', '{integer_pk.name}'), "
                    f"COALESCE((SELECT MAX({column_name}) FROM {table_name}), 1), "
                    f"EXISTS(SELECT 1 FROM {table_name})"
                    ")"
                )
            )

    for table_name, count in copied.items():
        print(f"{table_name}: {count} rows copied")
    print("SQLite to PostgreSQL migration completed.")
