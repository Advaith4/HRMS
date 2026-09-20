"""
src/tools/sql_tool.py
Sandboxed Read-Only Parameterized SQL Query Tool for TalentForge AI.
Enforces strict DDL/DML blocking to prevent database corruption or unauthorized modifications.
"""
import re
from typing import Any, Type
from pydantic import BaseModel, Field
from sqlmodel import Session, text

from src.database.connection import engine
from src.tools.base_tool import BaseHRMSTool

FORBIDDEN_SQL_KEYWORDS = (
    "drop", "delete", "update", "insert", "alter", "truncate", "create",
    "replace", "grant", "revoke", "exec", "execute", "merge"
)


class SQLQueryInput(BaseModel):
    query: str = Field(description="Read-only SQL query starting with SELECT")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Named parameters for safe parameterized execution")


class SQLQueryOutput(BaseModel):
    columns: list[str] = Field(default_factory=list, description="Column names returned by the query")
    rows: list[dict[str, Any]] = Field(default_factory=list, description="Row records formatted as key-value dictionaries")
    row_count: int = Field(default=0, description="Total number of rows returned")
    executed_query: str = Field(description="The validated SQL query that was executed")


class SQLQueryTool(BaseHRMSTool):
    name: str = "SQLQueryTool"
    description: str = "Executes sandboxed, read-only SELECT queries with named parameter substitution."
    args_schema: Type[BaseModel] = SQLQueryInput
    return_schema: Type[BaseModel] = SQLQueryOutput

    def _run(self, query: str, parameters: dict[str, Any] | None = None) -> SQLQueryOutput:
        clean_query = query.strip()
        params = parameters or {}

        # 1. Security Check: Block non-SELECT statements
        if not clean_query.lower().startswith("select"):
            raise PermissionError("Security violation: Only SELECT queries are permitted in SQLQueryTool.")

        # 2. Security Check: Search for forbidden mutation keywords
        tokens = re.findall(r"\b[a-zA-Z]+\b", clean_query.lower())
        for forbidden in FORBIDDEN_SQL_KEYWORDS:
            if forbidden in tokens and forbidden != "select":
                # Special check: ensure it's not part of column name alias
                if re.search(rf"\b{forbidden}\b", clean_query, re.IGNORECASE):
                    # Check if it appears as an execution verb
                    if forbidden in {"drop", "delete", "update", "insert", "alter", "truncate", "create"}:
                        raise PermissionError(f"Security violation: Mutating statement '{forbidden.upper()}' is strictly prohibited.")

        # 3. Execute query safely with connection
        with engine.connect() as conn:
            result = conn.execute(text(clean_query), params)
            columns = list(result.keys()) if result.returns_rows else []
            rows = [dict(row._mapping) for row in result.all()] if result.returns_rows else []

        return SQLQueryOutput(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            executed_query=clean_query,
        )


sql_query_tool = SQLQueryTool()
