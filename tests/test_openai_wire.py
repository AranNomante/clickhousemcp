"""Wire-level tests: the agent talks to a fake OpenAI-compatible server over real HTTP.

The model side uses pydantic-ai's real OpenAI provider (``OPENAI_BASE_URL`` + API key), and
the MCP side runs the real mcp-clickhouse server with a faked ClickHouse client. This covers
what scripted in-process models can't: provider selection from the model string, API-key
export, and whether the (summarized) history serializes into a request the API accepts.
"""

import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fake_openai_server import FakeOpenAIServer, output_tool_name, text, tool_call
from pydantic_ai.mcp import MCPServerStdio

import agent.clickhouse_agent as clickhouse_agent
from agent.clickhouse_agent import ClickHouseAgent
from agent.config import ModelAPIConfig, config, summarize_config
from agent.history_processor import SUMMARY_PREFIX

FAKE_CLICKHOUSE = Path(__file__).parent / "fixtures" / "fake_clickhouse_server.py"
MODEL = "openai-chat:gpt-4o-mini"  # plain "openai:" emits a pydantic-ai v2 deprecation warning
Step = Callable[[dict[str, Any]], dict[str, Any]]


class _FakeBackedServer(MCPServerStdio):  # type: ignore[misc]
    def __init__(self, command: str, args: list[str], **kwargs: Any) -> None:
        super().__init__(sys.executable, args=[str(FAKE_CLICKHOUSE)], **kwargs)


def _answer_orders_question() -> list[Step]:
    """Main-agent replies for one turn: list tables, run SQL, return structured output."""
    return [
        lambda body: tool_call("list_tables", {"database": "demo"}, "call_1"),
        lambda body: tool_call("run_query", {"query": "SELECT count() FROM demo.orders"}, "call_2"),
        lambda body: tool_call(output_tool_name(body), {"analysis": "There are 25 orders.", "confidence": 8}, "call_3"),
    ]


def _router(main_steps: list[Step], summary: str = "User asked how many orders; answer was 25.") -> Any:
    """Requests with tools go to the main-agent script; tool-less ones are the summarizer."""
    steps: Iterator[Step] = iter(main_steps)

    def handle(body: dict[str, Any]) -> dict[str, Any]:
        if not body.get("tools"):
            return text(summary)
        return next(steps)(body)

    return handle


def _contents(body: dict[str, Any], role: str) -> list[str]:
    return [str(m.get("content")) for m in body["messages"] if m.get("role") == role]


@pytest.fixture
def openai_agent_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Point the agent at the fake servers. Restores global config and env afterwards."""
    monkeypatch.setattr(clickhouse_agent, "MCPServerStdio", _FakeBackedServer)
    monkeypatch.setattr(config, "ai_model", config.ai_model)
    monkeypatch.setattr(config, "model_provider", config.model_provider)
    monkeypatch.setattr(config, "model_api", ModelAPIConfig())
    monkeypatch.setattr(summarize_config, "ai_model", MODEL)
    monkeypatch.setattr(summarize_config, "model_provider", "openai")
    monkeypatch.setattr(summarize_config, "model_api", ModelAPIConfig(OPENAI_API_KEY="test-key"))
    monkeypatch.setattr(summarize_config, "token_limit", summarize_config.token_limit)
    # A stale key in the environment must lose to the one set via set_model_api_key().
    monkeypatch.setenv("OPENAI_API_KEY", "stale-env-key")
    config.set_ai_model(MODEL)
    config.set_model_api_key("openai", "test-key")
    yield


@pytest.mark.asyncio
@pytest.mark.usefixtures("openai_agent_env")
async def test_full_run_over_openai_wire(monkeypatch: pytest.MonkeyPatch) -> None:
    with FakeOpenAIServer(_router(_answer_orders_question())) as server:
        monkeypatch.setenv("OPENAI_BASE_URL", server.base_url)
        result = await ClickHouseAgent().run(query="how many orders?")

    assert server.errors == []
    assert config.model_provider == "openai"  # derived from the model prefix
    assert server.auth_headers == ["Bearer test-key"] * 3
    assert result.analysis == "There are 25 orders."
    assert result.confidence == 8
    assert result.sql_used == ["SELECT count() FROM demo.orders"]
    # The real mcp-clickhouse result reached the model as a tool message.
    last_tool_messages = _contents(server.requests[-1], "tool")
    assert any("EXECUTED" in c for c in last_tool_messages)


@pytest.mark.asyncio
@pytest.mark.usefixtures("openai_agent_env")
async def test_summarized_history_is_accepted_by_the_api(monkeypatch: pytest.MonkeyPatch) -> None:
    summary = "User asked how many orders; answer was 25."
    follow_up = [
        lambda body: tool_call(output_tool_name(body), {"analysis": "Follow-up answered.", "confidence": 7}, "c4")
    ]
    monkeypatch.setattr(summarize_config, "token_limit", 1000)

    # prompt_tokens=5000 puts turn 1's context over the limit, so turn 2 summarizes first.
    with FakeOpenAIServer(_router(_answer_orders_question() + follow_up, summary), prompt_tokens=5000) as server:
        monkeypatch.setenv("OPENAI_BASE_URL", server.base_url)
        async with ClickHouseAgent() as agent:
            first = await agent.run(query="how many orders?")
            second = await agent.run(query="and how many products?", message_history=first.messages)

    assert server.errors == []
    assert second.analysis == "Follow-up answered."

    summarizer_requests = [r for r in server.requests if not r.get("tools")]
    assert len(summarizer_requests) == 1
    summarizer = summarizer_requests[0]
    assert any("Summarize" in c for c in _contents(summarizer, "system"))
    assert any("how many orders?" in c for c in _contents(summarizer, "user"))

    final = server.requests[-1]
    users = _contents(final, "user")
    assert SUMMARY_PREFIX + summary in users
    assert "and how many products?" in users
    assert _contents(final, "tool") == []  # turn-1 tool traffic was replaced by the summary
    assert all("how many orders?" != u for u in users)


@pytest.mark.asyncio
@pytest.mark.usefixtures("openai_agent_env")
async def test_history_below_limit_is_sent_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    follow_up = [lambda body: tool_call(output_tool_name(body), {"analysis": "ok", "confidence": 5}, "c4")]

    with FakeOpenAIServer(_router(_answer_orders_question() + follow_up), prompt_tokens=100) as server:
        monkeypatch.setenv("OPENAI_BASE_URL", server.base_url)
        async with ClickHouseAgent() as agent:
            first = await agent.run(query="how many orders?")
            await agent.run(query="and how many products?", message_history=first.messages)

    assert server.errors == []
    assert all(r.get("tools") for r in server.requests)  # no summarizer call under the default limit
    final = server.requests[-1]
    assert "how many orders?" in _contents(final, "user")
    assert len(_contents(final, "tool")) == 3  # list_tables, run_query, final_result from turn 1


def test_validator_rejects_invalid_histories() -> None:
    """The fake server's checks must actually catch the mistakes they claim to."""
    from fake_openai_server import validate_request

    starts_with_assistant = {"model": "m", "messages": [{"role": "assistant", "content": "hi"}]}
    unanswered_call = {
        "model": "m",
        "messages": [
            {"role": "user", "content": "q"},
            tool_call("run_query", {"query": "SELECT 1"}),
            {"role": "user", "content": "next"},
        ],
    }
    orphan_result = {
        "model": "m",
        "messages": [{"role": "user", "content": "q"}, {"role": "tool", "tool_call_id": "x", "content": "r"}],
    }

    assert validate_request(starts_with_assistant)
    assert validate_request(unanswered_call)
    assert validate_request(orphan_result)
    assert validate_request({"model": "m", "messages": [{"role": "user", "content": "q"}]}) == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("openai_agent_env")
async def test_api_rejection_is_an_execution_error_not_a_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # Pins the error mapping: a provider HTTP error must surface as AgentExecutionError
    # (chained from pydantic-ai's ModelHTTPError), not as MCPConnectionError.
    from pydantic_ai.exceptions import ModelHTTPError

    from agent.exceptions import AgentExecutionError, MCPConnectionError

    def reject(body: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("model exploded")  # fake server turns this into an HTTP 500

    with FakeOpenAIServer(reject) as server:
        monkeypatch.setenv("OPENAI_BASE_URL", server.base_url)
        with pytest.raises(AgentExecutionError) as excinfo:
            async with ClickHouseAgent() as agent:
                await agent.run(query="how many orders?")

    assert not isinstance(excinfo.value, MCPConnectionError)
    assert isinstance(excinfo.value.__cause__, ModelHTTPError)
