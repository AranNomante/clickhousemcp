"""Launch the REAL mcp-clickhouse MCP server over stdio, with only the ClickHouse network client faked.

Used by tests/test_contract.py. Everything between the agent and the database is the
production code path: pydantic-ai -> stdio -> mcp-clickhouse tools -> JSON serialization.
Only the HTTP client that would talk to a ClickHouse server is replaced by an in-memory catalog.
"""

import re
from types import SimpleNamespace
from typing import Any

import mcp_clickhouse.mcp_server as srv

CATALOG: dict[str, list[str]] = {
    "default": [],
    "demo": ["orders", "products"],
    "secret": ["salaries"],
}

_TABLE_FIELDS = [
    "database", "name", "engine", "create_table_query", "dependencies_database", "dependencies_table",
    "engine_full", "sorting_key", "primary_key", "total_rows", "total_bytes", "total_bytes_uncompressed",
    "parts", "active_parts", "total_marks", "comment",
]  # fmt: skip


def _like_to_regex(pattern: str) -> re.Pattern[str]:
    return re.compile("^" + re.escape(pattern).replace("%", ".*").replace("_", ".") + "$")


def _quoted(sql: str, key: str) -> str | None:
    m = re.search(key + r"\s*=?\s*'([^']*)'", sql)
    return m.group(1) if m else None


class FakeClient:
    server_version = "25.0"
    server_settings: dict[str, Any] = {}

    def command(self, sql: str, *args: Any, **kwargs: Any) -> str:
        if "SHOW DATABASES" in sql.upper():
            return "\n".join(CATALOG)
        return ""

    def query(self, sql: str, *args: Any, **kwargs: Any) -> SimpleNamespace:
        db = _quoted(sql, r"database\s*=")
        if "FROM system.tables" in sql and sql.strip().startswith("SELECT name"):
            names = CATALOG.get(db or "", [])
            like = _quoted(sql, r"name LIKE")
            if like is not None:
                names = [n for n in names if _like_to_regex(like).match(n)]
            return SimpleNamespace(result_rows=[[n] for n in names], column_names=["name"])
        if "FROM system.tables" in sql:
            requested = re.findall(r"'([^']*)'", sql.split(" IN ", 1)[1]) if " IN " in sql else []
            rows = [
                [db, n, "MergeTree", f"CREATE TABLE {db}.{n} (id UInt64)", "", "", "MergeTree", "id", "id",
                 1, 1, 1, 1, 1, 1, None]
                for n in requested
            ]  # fmt: skip
            return SimpleNamespace(result_rows=rows, column_names=_TABLE_FIELDS)
        if "FROM system.columns" in sql:
            table = _quoted(sql, r"table\s*=")
            cols = ["database", "table", "name", "column_type", "default_kind", "default_expression", "comment"]
            return SimpleNamespace(result_rows=[[db, table, "id", "UInt64", "", "", ""]], column_names=cols)
        # run_query: return a recognizable row so tests can tell whether the query executed.
        return SimpleNamespace(result_rows=[["EXECUTED", sql]], column_names=["status", "query"])

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        pass


srv.create_clickhouse_client = lambda *a, **k: FakeClient()
srv.get_readonly_setting = lambda client: "1"

if __name__ == "__main__":
    srv.mcp.run(transport="stdio")
