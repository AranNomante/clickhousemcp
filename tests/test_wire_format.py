"""Unit tests using the wire format mcp-clickhouse actually produces.

mcp-clickhouse tools return ``json.dumps(...)`` strings, and pydantic-ai passes those
strings to ``process_tool_call`` unparsed. Earlier tests mocked Python lists/dicts, which
hid the fact that allow-list filtering never ran against real responses.
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.clickhouse_agent import ClickHouseAgent, ClickHouseDependencies, _parse_tool_result


def _ctx(allowed_tables: list[str] | None = None, allowed_databases: list[str] | None = None) -> Any:
    ctx = MagicMock()
    ctx.deps = ClickHouseDependencies(
        host="localhost",
        port="8123",
        user="default",
        allowed_tables=allowed_tables,
        allowed_databases=allowed_databases,
    )
    return ctx


def _tables_payload(*names: str, database: str = "demo") -> str:
    return json.dumps(
        {
            "tables": [{"database": database, "name": n} for n in names],
            "next_page_token": None,
            "total_tables": len(names),
        }
    )


# ---------------------------------------------------------------------------
# _parse_tool_result
# ---------------------------------------------------------------------------


def test_parse_tool_result_decodes_json_list_and_dict() -> None:
    assert _parse_tool_result('["a", "b"]') == ["a", "b"]
    assert _parse_tool_result('  {"k": 1}  ') == {"k": 1}


def test_parse_tool_result_leaves_other_values_unchanged() -> None:
    assert _parse_tool_result("plain text") == "plain text"
    assert _parse_tool_result("[not json") == "[not json"
    assert _parse_tool_result(["already", "decoded"]) == ["already", "decoded"]
    assert _parse_tool_result(None) is None


# ---------------------------------------------------------------------------
# list_databases with JSON-string results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_databases_json_string_is_filtered() -> None:
    agent = ClickHouseAgent()
    call = AsyncMock(return_value=json.dumps(["default", "demo", "secret"]))

    result = await agent.process_tool_call(_ctx(allowed_databases=["demo"]), call, "list_databases", {})

    assert result == ["demo"]


@pytest.mark.asyncio
async def test_list_databases_unparseable_result_fails_closed() -> None:
    agent = ClickHouseAgent()
    call = AsyncMock(return_value="default\ndemo\nsecret")

    result = await agent.process_tool_call(_ctx(allowed_databases=["demo"]), call, "list_databases", {})

    assert result == []


@pytest.mark.asyncio
async def test_list_databases_without_allow_list_is_untouched() -> None:
    agent = ClickHouseAgent()
    raw = json.dumps(["default", "demo", "secret"])
    call = AsyncMock(return_value=raw)

    result = await agent.process_tool_call(_ctx(), call, "list_databases", {})

    assert result == raw


# ---------------------------------------------------------------------------
# list_tables with allowed_tables patterns and JSON-string results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tables_patterns_with_json_string_results() -> None:
    agent = ClickHouseAgent()

    async def call(name: str, args: dict[str, Any], _meta: Any = None) -> str:
        return {"orders": _tables_payload("orders"), "prod%": _tables_payload("products")}[args["like"]]

    result = await agent.process_tool_call(
        _ctx(allowed_tables=["orders", "prod%"], allowed_databases=["demo"]),
        call,  # type: ignore[arg-type]
        "list_tables",
        {"database": "demo"},
    )

    assert [t["name"] for t in result] == ["orders", "products"]


@pytest.mark.asyncio
async def test_list_tables_patterns_dedupe_across_json_results() -> None:
    agent = ClickHouseAgent()
    call = AsyncMock(return_value=_tables_payload("orders"))

    result = await agent.process_tool_call(
        _ctx(allowed_tables=["orders", "ord%"]), call, "list_tables", {"database": "demo"}
    )

    assert [t["name"] for t in result] == ["orders"]


@pytest.mark.asyncio
async def test_list_tables_patterns_unparseable_result_returns_nothing() -> None:
    agent = ClickHouseAgent()
    call = AsyncMock(return_value="not json")

    result = await agent.process_tool_call(_ctx(allowed_tables=["orders"]), call, "list_tables", {"database": "demo"})

    assert result == []
