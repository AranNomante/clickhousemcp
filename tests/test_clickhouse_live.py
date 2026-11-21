"""Live tests against a real ClickHouse server (no LLM; tool calls are scripted).

Skipped unless CLICKHOUSE_LIVE_TESTS=1. In CI a ClickHouse service container is seeded
with docker/init.sql plus a ``secret.salaries`` table (tests/fixtures/seed_live.py).

Run locally:
    docker compose up -d
    CLICKHOUSE_LIVE_TESTS=1 python tests/fixtures/seed_live.py
    CLICKHOUSE_LIVE_TESTS=1 pytest tests/test_clickhouse_live.py -v
"""

import os

import pytest
from scripted_model import as_obj, run_scripted

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(os.getenv("CLICKHOUSE_LIVE_TESTS") != "1", reason="set CLICKHOUSE_LIVE_TESTS=1"),
]


@pytest.fixture(autouse=True)
def live_config(monkeypatch: pytest.MonkeyPatch) -> None:
    from agent.config import config

    monkeypatch.setattr(config, "ai_model", "test")
    monkeypatch.setattr(config, "clickhouse_host", os.getenv("CLICKHOUSE_HOST", "localhost"))
    monkeypatch.setattr(config, "clickhouse_port", os.getenv("CLICKHOUSE_PORT", "8123"))
    monkeypatch.setattr(config, "clickhouse_user", os.getenv("CLICKHOUSE_USER", "default"))
    monkeypatch.setattr(config, "clickhouse_password", os.getenv("CLICKHOUSE_PASSWORD", ""))
    monkeypatch.setattr(config, "clickhouse_secure", "false")


async def test_list_databases_filtered_on_real_server() -> None:
    seen, _ = await run_scripted([("list_databases", {})], allowed_databases=["demo"])

    assert as_obj(seen["list_databases"]) == ["demo"]


async def test_list_databases_unrestricted_includes_secret() -> None:
    seen, _ = await run_scripted([("list_databases", {})])

    databases = as_obj(seen["list_databases"])
    assert "demo" in databases and "secret" in databases


async def test_allowed_tables_on_real_server() -> None:
    seen, _ = await run_scripted(
        [("list_tables", {"database": "demo"})],
        allowed_databases=["demo"],
        allowed_tables=["orders"],
    )

    assert [t["name"] for t in as_obj(seen["list_tables"])] == ["orders"]


async def test_run_query_returns_seeded_data() -> None:
    seen, result = await run_scripted([("run_query", {"query": "SELECT count() AS n FROM demo.orders"})])

    assert as_obj(seen["run_query"])["rows"] == [[25]]
    assert result.sql_used == ["SELECT count() AS n FROM demo.orders"]


async def test_run_query_is_read_only() -> None:
    await run_scripted([("run_query", {"query": "INSERT INTO demo.products VALUES (99, 'x', 'y', 1, 1)"})])

    count_seen, _ = await run_scripted([("run_query", {"query": "SELECT count() FROM demo.products WHERE id = 99"})])
    assert as_obj(count_seen["run_query"])["rows"] == [[0]]


async def test_run_query_not_restricted_by_allow_lists_known_limitation() -> None:
    """Allow-lists scope discovery only. Restricting reads needs ClickHouse GRANTs/roles."""
    seen, _ = await run_scripted(
        [("run_query", {"query": "SELECT count() FROM secret.salaries"})],
        allowed_databases=["demo"],
    )

    assert as_obj(seen["run_query"])["rows"] == [[2]]


# --- role= and query_timeout= (passed through to mcp-clickhouse) ----------------------

LIMITED_USER, LIMITED_PASSWORD = "agent_limited", "agent-limited-test"  # created by seed_live.py


@pytest.fixture
def limited_user(monkeypatch: pytest.MonkeyPatch) -> None:
    from agent.config import config

    monkeypatch.setattr(config, "clickhouse_user", LIMITED_USER)
    monkeypatch.setattr(config, "clickhouse_password", LIMITED_PASSWORD)


def _set(monkeypatch: pytest.MonkeyPatch, **options: object) -> None:
    from agent.config import config

    for name, value in options.items():
        monkeypatch.setattr(config, f"clickhouse_{name}", value)


@pytest.mark.usefixtures("limited_user")
async def test_role_blocks_reads_outside_its_grants(monkeypatch: pytest.MonkeyPatch) -> None:
    _set(monkeypatch, role="demo_reader")

    seen, result = await run_scripted([("run_query", {"query": "SELECT count() FROM secret.salaries"})])

    error = str(seen["run_query"])
    assert "ACCESS_DENIED" in error or "Not enough privileges" in error
    assert result.sql_used == ["SELECT count() FROM secret.salaries"]


@pytest.mark.usefixtures("limited_user")
async def test_role_allows_reads_inside_its_grants(monkeypatch: pytest.MonkeyPatch) -> None:
    _set(monkeypatch, role="demo_reader")
    seen, _ = await run_scripted([("run_query", {"query": "SELECT count() FROM demo.orders"})])
    assert as_obj(seen["run_query"])["rows"] == [[25]]

    # Same user, other role: now the secret table is readable. Shows the role is what decides.
    _set(monkeypatch, role="secret_reader")
    seen, _ = await run_scripted([("run_query", {"query": "SELECT count() FROM secret.salaries"})])
    assert as_obj(seen["run_query"])["rows"] == [[2]]


async def test_query_timeout_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    _set(monkeypatch, query_timeout=1)

    seen, _ = await run_scripted([("run_query", {"query": "SELECT sleep(3)"})])

    assert "timed out" in str(seen["run_query"]).lower()
