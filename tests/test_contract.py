"""Contract tests: ClickHouseAgent against the real mcp-clickhouse server.

The MCP server runs as a real stdio subprocess (tests/fixtures/fake_clickhouse_server.py);
only its ClickHouse network client is faked. The LLM is replaced by a scripted
``FunctionModel`` that issues exact tool calls, so these tests are deterministic and
need no API key.
"""

import json
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai.mcp import MCPServerStdio
from scripted_model import as_obj as _as_obj
from scripted_model import run_scripted as _run

import agent.clickhouse_agent as clickhouse_agent

FAKE_SERVER = Path(__file__).parent / "fixtures" / "fake_clickhouse_server.py"


class _FakeBackedServer(MCPServerStdio):  # type: ignore[misc]
    """Same constructor shape as MCPServerStdio, but launches the fake-backed real server."""

    def __init__(self, command: str, args: list[str], **kwargs: Any) -> None:
        super().__init__(sys.executable, args=[str(FAKE_SERVER)], **kwargs)


@pytest.fixture
def real_server(monkeypatch: pytest.MonkeyPatch) -> None:
    from agent.config import config

    monkeypatch.setattr(clickhouse_agent, "MCPServerStdio", _FakeBackedServer)
    monkeypatch.setattr(config, "ai_model", "test")


@pytest.mark.asyncio
@pytest.mark.usefixtures("real_server")
async def test_server_returns_json_strings() -> None:
    """Pins the wire format that hid the original bug: tool results arrive as JSON strings."""
    seen, _ = await _run([("list_databases", {})])

    assert isinstance(seen["list_databases"], str)
    assert json.loads(seen["list_databases"]) == ["default", "demo", "secret"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("real_server")
async def test_allowed_databases_filters_list_databases() -> None:
    seen, _ = await _run([("list_databases", {})], allowed_databases=["demo"])

    assert _as_obj(seen["list_databases"]) == ["demo"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("real_server")
async def test_allowed_databases_blocks_list_tables_on_other_database() -> None:
    seen, _ = await _run([("list_tables", {"database": "secret"})], allowed_databases=["demo"])

    assert _as_obj(seen["list_tables"]) == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("real_server")
async def test_allowed_tables_returns_matching_tables() -> None:
    seen, _ = await _run(
        [("list_tables", {"database": "demo"})],
        allowed_databases=["demo"],
        allowed_tables=["orders"],
    )

    tables = _as_obj(seen["list_tables"])
    assert [t["name"] for t in tables] == ["orders"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("real_server")
async def test_allowed_tables_supports_like_patterns() -> None:
    seen, _ = await _run(
        [("list_tables", {"database": "demo"})],
        allowed_tables=["ord%", "prod%"],
    )

    tables = _as_obj(seen["list_tables"])
    assert sorted(t["name"] for t in tables) == ["orders", "products"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("real_server")
async def test_run_query_is_not_restricted_by_allow_lists() -> None:
    """Documents a known limitation: allow-lists scope discovery, they do not filter SQL.

    Restricting what queries can read requires a ClickHouse user/role with limited GRANTs.
    If this test starts failing because queries ARE blocked, update the README accordingly.
    """
    sql = "SELECT * FROM secret.salaries"
    seen, result = await _run([("run_query", {"query": sql})], allowed_databases=["demo"])

    assert "EXECUTED" in str(seen["run_query"])
    assert result.sql_used == [sql]
