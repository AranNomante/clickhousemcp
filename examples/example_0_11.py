"""
0.11 feature showcase: reset(), run_batch(), cache, structlog.

Prerequisites:
    docker compose up -d
    uv pip install -e ".[dev]"

Set your API key:
    export GOOGLE_API_KEY=...
"""

import asyncio
import os
import time

from agent.clickhouse_agent import ClickHouseAgent
from agent.config import config

config.set_log_level("INFO")
config.set_clickhouse(host="localhost", port="8123", user="default", password="", secure="false")
config.set_ai_model(os.environ.get("AI_MODEL", "google:gemini-3.1-flash-lite"))
config.set_model_api_key("google", os.environ.get("GOOGLE_API_KEY", ""))


# ---------------------------------------------------------------------------
# 1. reset() — tear down and re-arm without re-instantiating
# ---------------------------------------------------------------------------


async def demo_reset() -> None:
    print("\n=== 1. reset() ===")
    agent = ClickHouseAgent()

    result = await agent.run(
        query="How many rows are in demo.orders?",
        allowed_databases=["demo"],
    )
    print(f"First run:  {result.analysis}")
    print(f"SQL used:   {result.sql_used}")

    await agent.reset()
    print("Agent reset — server torn down, will re-initialize on next run().")

    result2 = await agent.run(
        query="How many rows are in demo.products?",
        allowed_databases=["demo"],
    )
    print(f"After reset: {result2.analysis}")


# ---------------------------------------------------------------------------
# 2. run_batch() — parallel queries, one MCP server
# ---------------------------------------------------------------------------


async def demo_run_batch() -> None:
    print("\n=== 2. run_batch() ===")
    queries = [
        "How many orders are there?",
        "How many products are there?",
        "What is the total revenue across all orders?",
    ]

    async with ClickHouseAgent() as agent:
        t0 = time.perf_counter()
        results = await agent.run_batch(queries, allowed_databases=["demo"])
        elapsed = time.perf_counter() - t0

    print(f"All {len(results)} queries finished in {elapsed:.1f}s (concurrent).")
    for q, r in zip(queries, results):
        print(f"\n  Q: {q}")
        print(f"  A: {r.analysis}")
        print(f"  SQL: {r.sql_used}")


# ---------------------------------------------------------------------------
# 3. Cache — second identical call returns instantly
# ---------------------------------------------------------------------------


async def demo_cache() -> None:
    print("\n=== 3. Query result cache ===")
    agent = ClickHouseAgent(enable_cache=True)

    query = "How many orders are there?"

    t0 = time.perf_counter()
    result1 = await agent.run(query=query, allowed_databases=["demo"])
    first_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    result2 = await agent.run(query=query, allowed_databases=["demo"])
    cached_ms = (time.perf_counter() - t0) * 1000

    print(f"First call:  {first_ms:.0f}ms  — {result1.analysis}")
    print(f"Cached call: {cached_ms:.0f}ms  — same object: {result1 is result2}")


# ---------------------------------------------------------------------------
# 4. structlog — install clickhouse-mcp-agent[logging] to activate
# ---------------------------------------------------------------------------


async def demo_structlog() -> None:
    print("\n=== 4. structlog ===")
    try:
        import structlog  # type: ignore[import-not-found]  # noqa: F401

        print("structlog is installed — structured logs are active above.")
    except ImportError:
        print("structlog not installed. Run: pip install 'clickhouse-mcp-agent[logging]'")
        print("Then re-run this example to see structured JSON log output.")

    # Run a quick query so any log output is visible.
    agent = ClickHouseAgent()
    result = await agent.run(
        query="List available tables.",
        allowed_databases=["demo"],
    )
    print(f"Result: {result.analysis}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    await demo_reset()
    await demo_run_batch()
    await demo_cache()
    await demo_structlog()


if __name__ == "__main__":
    asyncio.run(main())
