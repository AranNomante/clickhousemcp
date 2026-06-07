"""
Integration example: exercises every major feature with minimal API calls.

Prerequisites:
    docker compose up -d
    uv pip install -e ".[dev]"

Set your API key via environment variable or replace the placeholder below.
"""

import asyncio
import os
import time

from agent.clickhouse_agent import ClickHouseAgent
from agent.exceptions import AgentExecutionError, MCPConnectionError
from pydantic_ai import Agent

config_done = False


def setup() -> None:
    from agent.config import config
    config.set_log_level("WARNING")  # suppress noise during integration run
    config.set_clickhouse(host="localhost", port="8123", user="default", password="", secure="false")
    config.set_ai_model(os.environ.get("AI_MODEL", "google:gemini-3.1-flash-lite"))
    config.set_model_api_key("google", os.environ.get("GOOGLE_API_KEY", ""))


def ok(label: str) -> None:
    print(f"  ✓ {label}")


def section(title: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


# ---------------------------------------------------------------------------
# 1. One-shot run() with allowed_databases
# ---------------------------------------------------------------------------


async def test_run() -> None:
    section("1. run() — one-shot, allowed_databases")
    agent = ClickHouseAgent()
    result = await agent.run(
        query="How many rows are in demo.orders?",
        allowed_databases=["demo"],
    )
    assert result.analysis, "analysis is empty"
    assert result.confidence > 0, f"confidence not positive: {result.confidence}"
    assert result.sql_used, "no SQL captured"
    ok(f"analysis: {result.analysis[:80]}")
    ok(f"sql_used: {result.sql_used}")
    ok(f"confidence: {result.confidence}")


# ---------------------------------------------------------------------------
# 2. allowed_tables restriction
# ---------------------------------------------------------------------------


async def test_allowed_tables() -> None:
    section("2. allowed_tables — restrict to orders only")
    agent = ClickHouseAgent()
    result = await agent.run(
        query="List available tables.",
        allowed_databases=["demo"],
        allowed_tables=["orders"],  # products should not appear
    )
    assert result.analysis, "analysis is empty"
    ok(f"analysis: {result.analysis[:80]}")
    ok("allowed_tables filter applied")


# ---------------------------------------------------------------------------
# 3. Persistent server + run_batch()
# ---------------------------------------------------------------------------


async def test_run_batch() -> None:
    section("3. run_batch() — 2 concurrent queries, persistent server")
    async with ClickHouseAgent() as agent:
        t0 = time.perf_counter()
        results = await agent.run_batch(
            ["How many orders are there?", "How many products are there?"],
            allowed_databases=["demo"],
        )
        elapsed = time.perf_counter() - t0

    assert len(results) == 2
    for r in results:
        assert r.sql_used, "no SQL captured for batch query"
    ok(f"2 queries in {elapsed:.1f}s (concurrent)")
    ok(f"Q1 sql: {results[0].sql_used}")
    ok(f"Q2 sql: {results[1].sql_used}")


# ---------------------------------------------------------------------------
# 4. run_stream()
# ---------------------------------------------------------------------------


async def test_stream() -> None:
    section("4. run_stream() — streamed nodes")
    agent = ClickHouseAgent()
    node_count = 0
    async for _ in agent.run_stream(
        query="How many rows in demo.orders?",
        allowed_databases=["demo"],
    ):
        node_count += 1
    assert node_count > 0, "no nodes yielded"
    ok(f"streamed {node_count} nodes")


# ---------------------------------------------------------------------------
# 5. Query result cache
# ---------------------------------------------------------------------------


async def test_cache() -> None:
    section("5. enable_cache=True — second call returns instantly")
    agent = ClickHouseAgent(enable_cache=True)
    query = "How many rows in demo.orders?"

    t0 = time.perf_counter()
    r1 = await agent.run(query=query, allowed_databases=["demo"])
    first_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    r2 = await agent.run(query=query, allowed_databases=["demo"])
    cached_ms = (time.perf_counter() - t0) * 1000

    assert r1 is r2, "cache miss — same object expected"
    assert cached_ms < 50, f"cached call took {cached_ms:.0f}ms, expected <50ms"
    ok(f"first: {first_ms:.0f}ms")
    ok(f"cached: {cached_ms:.1f}ms  (same object: {r1 is r2})")


# ---------------------------------------------------------------------------
# 6. Multi-turn conversation via message_history
# ---------------------------------------------------------------------------


async def test_message_history() -> None:
    section("6. message_history — multi-turn conversation")
    async with ClickHouseAgent() as agent:
        r1 = await agent.run(
            query="How many orders are there?",
            allowed_databases=["demo"],
        )
        r2 = await agent.run(
            query="And how many products?",
            allowed_databases=["demo"],
            message_history=r1.messages,
        )
    assert r2.analysis, "second turn analysis is empty"
    assert r2.messages, "no messages on second turn"
    ok(f"turn 1: {r1.analysis[:60]}")
    ok(f"turn 2: {r2.analysis[:60]}")
    ok(f"total messages: {len(r2.messages)}")


# ---------------------------------------------------------------------------
# 7. reset()
# ---------------------------------------------------------------------------


async def test_reset() -> None:
    section("7. reset() — tear down and re-arm")
    agent = ClickHouseAgent()
    await agent.run(query="How many orders?", allowed_databases=["demo"])
    assert agent.agent is not None

    await agent.reset()
    assert agent.agent is None
    assert agent.server is None
    assert agent._sql_used == []
    assert agent._cache == {}

    # Re-initializes on next call
    r = await agent.run(query="How many products?", allowed_databases=["demo"])
    assert r.analysis
    ok("reset cleared agent and server")
    ok("re-initialized on next run()")
    ok(f"post-reset analysis: {r.analysis[:60]}")


# ---------------------------------------------------------------------------
# 8. Error handling
# ---------------------------------------------------------------------------


async def test_error_handling() -> None:
    section("8. Error handling — typed exceptions")
    from agent.exceptions import AgentExecutionError, ClickHouseMCPError, MCPConnectionError

    assert issubclass(MCPConnectionError, ClickHouseMCPError)
    assert issubclass(AgentExecutionError, ClickHouseMCPError)

    try:
        raise MCPConnectionError("simulated")
    except ClickHouseMCPError as e:
        ok(f"MCPConnectionError caught as ClickHouseMCPError: {e}")

    try:
        raise AgentExecutionError("simulated")
    except ClickHouseMCPError as e:
        ok(f"AgentExecutionError caught as ClickHouseMCPError: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    setup()
    print("\n=== clickhouse-mcp-agent integration example ===")

    await test_run()
    await test_allowed_tables()
    await test_run_batch()
    await test_stream()
    await test_cache()
    await test_message_history()
    await test_reset()
    await test_error_handling()

    print("\n" + "═" * 50)
    print("  All checks passed.")
    print("═" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
