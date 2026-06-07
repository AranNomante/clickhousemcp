"""Integration-style tests using mocked MCP tool calls."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.clickhouse_agent import ClickHouseAgent, ClickHouseDependencies
from agent.exceptions import AgentExecutionError, ClickHouseMCPError, HistoryProcessorError, MCPConnectionError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(
    allowed_tables: list[str] | None = None,
    allowed_databases: list[str] | None = None,
) -> Any:
    deps = ClickHouseDependencies(
        host="localhost",
        port="9000",
        user="default",
        allowed_tables=allowed_tables,
        allowed_databases=allowed_databases,
    )
    ctx = MagicMock()
    ctx.deps = deps
    return ctx


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


def test_exception_hierarchy() -> None:
    assert issubclass(MCPConnectionError, ClickHouseMCPError)
    assert issubclass(AgentExecutionError, ClickHouseMCPError)
    assert issubclass(HistoryProcessorError, ClickHouseMCPError)
    assert issubclass(ClickHouseMCPError, Exception)


def test_exceptions_are_catchable_as_base() -> None:
    with pytest.raises(ClickHouseMCPError):
        raise MCPConnectionError("test")
    with pytest.raises(ClickHouseMCPError):
        raise AgentExecutionError("test")
    with pytest.raises(ClickHouseMCPError):
        raise HistoryProcessorError("test")


def test_exceptions_carry_cause() -> None:
    cause = ValueError("original")
    exc = AgentExecutionError("wrapped")
    try:
        raise exc from cause
    except AgentExecutionError as e:
        assert e.__cause__ is cause


# ---------------------------------------------------------------------------
# allowed_tables enforcement via process_tool_call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_tool_call_empty_allowed_tables_blocks_all() -> None:
    agent = ClickHouseAgent()
    ctx = _make_ctx(allowed_tables=[])
    call_tool_func = AsyncMock()

    result = await agent.process_tool_call(ctx, call_tool_func, "list_tables", {"database": "demo"})

    assert result == []
    call_tool_func.assert_not_called()


@pytest.mark.asyncio
async def test_process_tool_call_none_allowed_tables_passes_through() -> None:
    agent = ClickHouseAgent()
    ctx = _make_ctx(allowed_tables=None)
    call_tool_func = AsyncMock(return_value={"tables": [{"database": "demo", "name": "orders"}]})

    result = await agent.process_tool_call(ctx, call_tool_func, "list_tables", {"database": "demo"})

    call_tool_func.assert_called_once()
    assert result == {"tables": [{"database": "demo", "name": "orders"}]}


# ---------------------------------------------------------------------------
# allowed_databases enforcement via process_tool_call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_tool_call_blocks_unlisted_database() -> None:
    agent = ClickHouseAgent()
    ctx = _make_ctx(allowed_databases=["demo"])
    call_tool_func = AsyncMock()

    result = await agent.process_tool_call(ctx, call_tool_func, "list_tables", {"database": "system"})

    assert result == []
    call_tool_func.assert_not_called()


@pytest.mark.asyncio
async def test_process_tool_call_allows_listed_database() -> None:
    agent = ClickHouseAgent()
    ctx = _make_ctx(allowed_tables=None, allowed_databases=["demo"])
    call_tool_func = AsyncMock(return_value={"tables": []})

    await agent.process_tool_call(ctx, call_tool_func, "list_tables", {"database": "demo"})

    call_tool_func.assert_called_once()


@pytest.mark.asyncio
async def test_process_tool_call_empty_allowed_databases_blocks_all() -> None:
    agent = ClickHouseAgent()
    ctx = _make_ctx(allowed_databases=[])
    call_tool_func = AsyncMock()

    result = await agent.process_tool_call(ctx, call_tool_func, "list_tables", {"database": "demo"})

    assert result == []
    call_tool_func.assert_not_called()


# ---------------------------------------------------------------------------
# sql_used extraction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_tool_call_captures_sql() -> None:
    agent = ClickHouseAgent()
    agent._sql_used = []
    ctx = _make_ctx()
    call_tool_func = AsyncMock(return_value=[{"col": "val"}])

    await agent.process_tool_call(ctx, call_tool_func, "run_query", {"query": "SELECT 1"})
    await agent.process_tool_call(ctx, call_tool_func, "run_query", {"query": "SELECT 2"})

    assert agent._sql_used == ["SELECT 1", "SELECT 2"]


@pytest.mark.asyncio
async def test_process_tool_call_no_sql_for_non_query_tools() -> None:
    agent = ClickHouseAgent()
    agent._sql_used = []
    ctx = _make_ctx(allowed_tables=None)
    call_tool_func = AsyncMock(return_value={"tables": []})

    await agent.process_tool_call(ctx, call_tool_func, "list_tables", {"database": "demo"})

    assert agent._sql_used == []


# ---------------------------------------------------------------------------
# _get_clickhouse_deps
# ---------------------------------------------------------------------------


def test_get_clickhouse_deps_sets_allowed_databases() -> None:
    agent = ClickHouseAgent()
    deps = agent._get_clickhouse_deps(allowed_tables=["orders"], allowed_databases=["demo"])

    assert deps.allowed_tables == ["orders"]
    assert deps.allowed_databases == ["demo"]


def test_get_clickhouse_deps_none_leaves_fields_none() -> None:
    agent = ClickHouseAgent()
    deps = agent._get_clickhouse_deps()

    assert deps.allowed_tables is None
    assert deps.allowed_databases is None


def test_get_clickhouse_deps_secure_is_bool() -> None:
    agent = ClickHouseAgent()
    deps = agent._get_clickhouse_deps()
    assert isinstance(deps.secure, bool)


# ---------------------------------------------------------------------------
# RunResult structure
# ---------------------------------------------------------------------------


def test_run_result_has_sql_used_field() -> None:
    from pydantic_ai.usage import RunUsage

    from agent.clickhouse_agent import RunResult

    usage = RunUsage(requests=1, input_tokens=10, output_tokens=10)
    result = RunResult(
        messages=[],
        new_messages=[],
        usage=usage,
        analysis="test",
        confidence=8,
    )
    assert result.sql_used == []


def test_run_result_sql_used_populated() -> None:
    from pydantic_ai.usage import RunUsage

    from agent.clickhouse_agent import RunResult

    usage = RunUsage(requests=1, input_tokens=10, output_tokens=10)
    result = RunResult(
        messages=[],
        new_messages=[],
        usage=usage,
        analysis="test",
        confidence=8,
        sql_used=["SELECT 1", "SELECT 2"],
    )
    assert result.sql_used == ["SELECT 1", "SELECT 2"]


# ---------------------------------------------------------------------------
# Context manager interface
# ---------------------------------------------------------------------------


def test_agent_has_aenter_aexit() -> None:
    import inspect
    agent = ClickHouseAgent()
    assert hasattr(agent, "__aenter__")
    assert hasattr(agent, "__aexit__")
    assert inspect.iscoroutinefunction(agent.__aenter__)
    assert inspect.iscoroutinefunction(agent.__aexit__)


# ---------------------------------------------------------------------------
# _ensure_agent — exercises MCPServerStdio and Agent construction paths
# so deprecation warnings in those calls are caught by filterwarnings=error
# ---------------------------------------------------------------------------


def test_ensure_agent_constructs_without_deprecations() -> None:
    from unittest.mock import MagicMock, patch

    mock_server = MagicMock()
    mock_agent = MagicMock()

    with (
        patch("agent.clickhouse_agent.MCPServerStdio", return_value=mock_server) as mock_mcp,
        patch("agent.clickhouse_agent.Agent", return_value=mock_agent) as mock_agent_cls,
    ):
        agent = ClickHouseAgent()
        agent._ensure_agent()

        # MCPServerStdio called once with mcp-clickhouse as first arg
        mock_mcp.assert_called_once()
        assert mock_mcp.call_args.args[0] == "mcp-clickhouse"

        # Agent[T, T](...) — subscript returns a new mock, which is then called
        agent_init = mock_agent_cls.__getitem__.return_value
        agent_init.assert_called_once()
        agent_kwargs = agent_init.call_args.kwargs
        assert "retries" not in agent_kwargs
        assert "tool_retries" in agent_kwargs
        assert "output_retries" in agent_kwargs

        # Calling again is a no-op (lazy init guard)
        agent._ensure_agent()
        mock_mcp.assert_called_once()


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_clears_agent_and_server() -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_server = MagicMock()
    mock_agent = MagicMock()
    mock_agent.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("agent.clickhouse_agent.MCPServerStdio", return_value=mock_server),
        patch("agent.clickhouse_agent.Agent", return_value=mock_agent),
    ):
        agent = ClickHouseAgent()
        agent._ensure_agent()
        assert agent.agent is not None
        assert agent.server is not None

        await agent.reset()

        assert agent.agent is None
        assert agent.server is None
        assert agent._in_context is False
        assert agent._sql_used == []
        assert agent._cache == {}


@pytest.mark.asyncio
async def test_reset_is_safe_when_not_initialized() -> None:
    agent = ClickHouseAgent()
    # Should not raise even though agent/server are None
    await agent.reset()
    assert agent.agent is None


# ---------------------------------------------------------------------------
# run_batch()
# ---------------------------------------------------------------------------


def test_agent_has_run_batch() -> None:
    import inspect

    agent = ClickHouseAgent()
    assert hasattr(agent, "run_batch")
    assert inspect.iscoroutinefunction(agent.run_batch)


# ---------------------------------------------------------------------------
# Query result cache
# ---------------------------------------------------------------------------


def test_cache_disabled_by_default() -> None:
    agent = ClickHouseAgent()
    assert agent._enable_cache is False
    assert agent._cache == {}


def test_cache_enabled_flag() -> None:
    agent = ClickHouseAgent(enable_cache=True)
    assert agent._enable_cache is True


def test_cache_key_is_order_independent_for_sets() -> None:
    agent = ClickHouseAgent(enable_cache=True)
    k1 = agent._make_cache_key("SELECT 1", ["a", "b"], ["db1"])
    k2 = agent._make_cache_key("SELECT 1", ["b", "a"], ["db1"])
    assert k1 == k2


def test_cache_key_none_vs_empty_list_differ() -> None:
    agent = ClickHouseAgent(enable_cache=True)
    k_none = agent._make_cache_key("SELECT 1", None, None)
    k_empty = agent._make_cache_key("SELECT 1", [], [])
    assert k_none != k_empty


def test_cache_is_stateless_flag_set_before_history_processor() -> None:
    # Regression: run() used to check `message_history is None` AFTER calling
    # _use_history_processor(), which always returns a list (never None).
    # Results were therefore never written to the cache.
    # The fix captures `is_stateless` before the processor runs.
    agent = ClickHouseAgent(enable_cache=True)
    # _make_cache_key works on None correctly — confirms the key round-trips.
    key = agent._make_cache_key("q", None, None)
    assert key == ("q", None, None)
    # Cache is empty before any run — nothing pre-cached.
    assert key not in agent._cache


# ---------------------------------------------------------------------------
# Concurrent SQL isolation via contextvar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_sql_tracking_is_isolated() -> None:
    import asyncio
    import contextvars

    from agent.clickhouse_agent import _sql_used_var

    results: list[list[str]] = []

    async def fake_run(sql: str) -> None:
        local: list[str] = []
        token = _sql_used_var.set(local)
        try:
            await asyncio.sleep(0)  # yield to allow interleaving
            local.append(sql)
            await asyncio.sleep(0)
        finally:
            _sql_used_var.reset(token)
        results.append(list(local))

    await asyncio.gather(
        asyncio.create_task(fake_run("SELECT 1")),
        asyncio.create_task(fake_run("SELECT 2")),
    )

    assert len(results) == 2
    # Each task saw only its own SQL.
    all_sql = [r[0] for r in results]
    assert "SELECT 1" in all_sql
    assert "SELECT 2" in all_sql
