"""Regression tests for the 0.12.2 fixes (history summarization, config, cache, errors)."""

import importlib
import sys
from typing import Any

import pytest
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RequestUsage, RunUsage

from agent.clickhouse_agent import ClickHouseAgent, RunResult, _is_connection_error
from agent.config import (
    ClickHouseConfig,
    EnvConfig,
    ModelAPIConfig,
    SummarizeAgentEnv,
    apply_api_key,
    provider_from_model,
    summarize_config,
)

# `agent.history_processor` the attribute is the re-exported function; load the module itself.
hp = importlib.import_module("agent.history_processor")


def _history(input_tokens: int = 10, output_tokens: int = 5) -> list[ModelMessage]:
    return [
        ModelRequest(parts=[UserPromptPart("how many orders?")]),
        ModelResponse(
            parts=[TextPart("25 orders")], usage=RequestUsage(input_tokens=input_tokens, output_tokens=output_tokens)
        ),
    ]


# --- history summarization ----------------------------------------------------


@pytest.mark.asyncio
async def test_summarize_returns_user_message_with_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression: used to return new_messages()[0], an empty ModelRequest, dropping the summary.
    monkeypatch.setattr(summarize_config, "ai_model", TestModel(custom_output_text="User asked about orders."))

    out = await hp.summarize_old_messages(_history())

    assert len(out) == 1
    assert isinstance(out[0], ModelRequest)
    part = out[0].parts[0]
    assert isinstance(part, UserPromptPart)
    assert part.content == hp.SUMMARY_PREFIX + "User asked about orders."


@pytest.mark.asyncio
async def test_history_processor_skips_without_summarizer_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(summarize_config, "model_provider", "google")
    monkeypatch.setattr(summarize_config, "model_api", ModelAPIConfig())
    monkeypatch.setattr(summarize_config, "token_limit", 10)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    history = _history()

    assert await hp.history_processor(1000, history, "openai") is history


@pytest.mark.asyncio
async def test_history_processor_uses_summarizer_key_across_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression: summarize_config's key was never applied, and a provider mismatch always skipped.
    monkeypatch.setattr(summarize_config, "model_provider", "google")
    monkeypatch.setattr(summarize_config, "model_api", ModelAPIConfig(GOOGLE_API_KEY="g-key"))
    monkeypatch.setattr(summarize_config, "token_limit", 10)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    called: list[int] = []

    async def fake_summarize(messages: list[ModelMessage]) -> list[ModelMessage]:
        called.append(len(messages))
        return []

    monkeypatch.setattr(hp, "summarize_old_messages", fake_summarize)
    await hp.history_processor(1000, _history(), "openai")

    assert called == [2]
    import os

    assert os.environ["GOOGLE_API_KEY"] == "g-key"


@pytest.mark.asyncio
async def test_token_count_uses_latest_response_not_sum(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []

    async def fake_processor(total: int, messages: list[ModelMessage], provider: str) -> list[ModelMessage]:
        seen.append(total)
        return messages

    monkeypatch.setattr(hp, "history_processor", fake_processor)
    history = _history(100, 10) + _history(300, 20)  # latest context = 320, sum would be 430

    await ClickHouseAgent()._use_history_processor(history)

    assert seen == [320]


# --- config ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("model", "provider"),
    [
        ("openai:gpt-4o-mini", "openai"),
        ("google-gla:gemini-2.5-flash", "google"),
        ("cohere:command-r-plus", "co"),
        ("xai:grok-4", "xai"),
        ("groq:llama-3.3-70b-versatile", "groq"),
        ("ollama:llama3", None),
        ("test", None),
    ],
)
def test_provider_from_model(model: str, provider: str | None) -> None:
    assert provider_from_model(model) == provider


def test_set_ai_model_updates_provider() -> None:
    # Regression: changing the model left model_provider on "google", so the wrong key was used.
    cfg, scfg = EnvConfig(), SummarizeAgentEnv()
    cfg.set_ai_model("anthropic:claude-sonnet-4-6")
    scfg.set_ai_model("openai:gpt-4o-mini")
    assert cfg.model_provider == "anthropic"
    assert scfg.model_provider == "openai"


def test_apply_api_key_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression: setdefault meant an explicitly configured key never replaced an existing env var.
    monkeypatch.setenv("OPENAI_API_KEY", "old")
    assert apply_api_key(ModelAPIConfig(OPENAI_API_KEY="new"), "openai")
    import os

    assert os.environ["OPENAI_API_KEY"] == "new"


def test_apply_api_key_unknown_provider_is_not_blocked() -> None:
    assert apply_api_key(ModelAPIConfig(), "ollama")


def test_use_connection_preset_and_custom() -> None:
    cfg = EnvConfig()
    cfg.use_connection("local")
    assert (cfg.clickhouse_host, cfg.clickhouse_port, cfg.clickhouse_secure) == ("localhost", "8123", "false")

    cfg.use_connection(ClickHouseConfig(name="x", host="ch.internal", port="8443", user="u", password="p"))
    assert (cfg.clickhouse_host, cfg.clickhouse_user, cfg.clickhouse_password) == ("ch.internal", "u", "p")

    with pytest.raises(ValueError):
        cfg.use_connection("nope")


# --- agent ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_returns_copies(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = ClickHouseAgent(enable_cache=True)
    cached = RunResult(messages=[], new_messages=[], usage=RunUsage(), analysis="a", confidence=5, sql_used=["S"])
    agent._cache[agent._make_cache_key("q", None, None)] = cached

    first = await agent.run(query="q")
    first.sql_used.append("mutated")
    second = await agent.run(query="q")

    assert second.sql_used == ["S"]


@pytest.mark.skipif(sys.version_info < (3, 11), reason="ExceptionGroup is builtin from 3.11")
def test_connection_error_detection() -> None:
    group: Any = ExceptionGroup("unhandled errors in a TaskGroup", [OSError("boom")])  # noqa: F821
    assert _is_connection_error(group)
    assert not _is_connection_error(ValueError("bad output"))


# --- improvements -----------------------------------------------------------------


def test_set_clickhouse_accepts_typed_values_and_extra_settings() -> None:
    cfg = EnvConfig()
    cfg.set_clickhouse(port=8123, secure=False, role="agent_reader", query_timeout=60, verify=True)
    env = cfg.mcp_server_env()
    assert env["CLICKHOUSE_PORT"] == "8123"
    assert env["CLICKHOUSE_SECURE"] == "false"
    assert env["CLICKHOUSE_ROLE"] == "agent_reader"
    assert env["CLICKHOUSE_MCP_QUERY_TIMEOUT"] == "60"
    assert env["CLICKHOUSE_VERIFY"] == "true"
    assert "CLICKHOUSE_DATABASE" not in env  # unset options don't override server defaults


def test_mcp_server_launched_with_current_interpreter() -> None:
    agent = ClickHouseAgent()
    agent._ensure_agent()
    assert agent.server is not None
    assert agent.server.command == sys.executable
    assert agent.server.args == ["-m", "mcp_clickhouse.main"]


@pytest.mark.asyncio
async def test_run_batch_return_exceptions_keeps_other_results(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = ClickHouseAgent()
    ok = RunResult(messages=[], new_messages=[], usage=RunUsage(), analysis="ok", confidence=5)

    async def fake_run(*, query: str, **_: Any) -> RunResult:
        if query == "bad":
            raise ValueError("boom")
        return ok

    monkeypatch.setattr(agent, "run", fake_run)
    results = await agent.run_batch(["good", "bad"], return_exceptions=True)

    assert results[0] is ok
    assert isinstance(results[1], ValueError)


def test_default_token_limit_is_above_per_request_overhead() -> None:
    # 1000 was below the ~600-token tool/instruction overhead plus any query result,
    # so every follow-up turn was summarized.
    assert SummarizeAgentEnv().token_limit == 50_000
