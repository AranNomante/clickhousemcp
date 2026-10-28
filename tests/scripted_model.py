"""Shared helpers: drive ClickHouseAgent with a scripted model instead of a real LLM."""

import json
from typing import Any

from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from agent.clickhouse_agent import ClickHouseAgent, RunResult


def scripted_model(calls: list[tuple[str, dict[str, Any]]], seen: dict[str, Any]) -> FunctionModel:
    """A model that makes the given tool calls in order, then returns a final answer.

    Every tool result the agent receives is recorded in ``seen`` keyed by tool name.
    """
    step = {"n": 0}

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        for m in messages:
            for part in getattr(m, "parts", []):
                if isinstance(part, ToolReturnPart):
                    seen[part.tool_name] = part.content
        step["n"] += 1
        if step["n"] <= len(calls):
            name, args = calls[step["n"] - 1]
            return ModelResponse(parts=[ToolCallPart(name, args)])
        final = info.output_tools[0].name
        return ModelResponse(parts=[ToolCallPart(final, {"analysis": "done", "confidence": 5})])

    return FunctionModel(model)


async def run_scripted(
    calls: list[tuple[str, dict[str, Any]]], **run_kwargs: Any
) -> tuple[dict[str, Any], RunResult]:
    """Run ClickHouseAgent once with a scripted model; return (tool results seen, RunResult)."""
    seen: dict[str, Any] = {}
    agent = ClickHouseAgent()
    agent._ensure_agent()
    assert agent.agent is not None
    with agent.agent.override(model=scripted_model(calls, seen)):
        result = await agent.run(query="q", **run_kwargs)
    return seen, result


def as_obj(value: Any) -> Any:
    """Decode a tool result that may still be a JSON string."""
    return json.loads(value) if isinstance(value, str) else value
