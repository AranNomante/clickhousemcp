"""ClickHouse support agent that combines PydanticAI with ClickHouse MCP server.

This agent uses a similar pattern to the bank support example but integrates
with ClickHouse via MCP server for database queries.
"""

import os
import asyncio

from dataclasses import dataclass
from typing import Optional, Any, Dict, List
from enum import Enum

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio, RunContext, CallToolFunc
from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import RunUsage


import logging


# Enum for supported model providers
class ModelProvider(Enum):
    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    MISTRAL = "mistral"
    CO = "co"


logger = logging.getLogger(__name__)


@dataclass
class ClickHouseDependencies:
    """Dependencies for ClickHouse connection and MCP server configuration."""

    host: str
    port: str
    user: str
    password: str = ""
    secure: str = "true"
    allowed_tables: Optional[list[str]] = None


@dataclass
class ClickHouseOutput:
    """Output structure for ClickHouse agent responses."""

    """Analysis of the query result."""
    analysis: str

    """Confidence level of the analysis (1-10)."""
    confidence: int


@dataclass
class RunResult:
    """Result structure for agent run method."""

    """Messages exchanged during the query."""
    messages: list[ModelMessage]

    """New messages added during the query execution."""
    new_messages: list[ModelMessage]

    usage: RunUsage

    """Analysis of the query result."""
    analysis: str

    """Confidence level of the analysis (1-10)."""
    confidence: int

    """Last message in the conversation, useful for context."""
    last_message: Optional[ModelMessage] = None


class ClickHouseAgent:
    """
    ClickHouse MCP Agent that uses PydanticAI for database queries.

    This agent integrates with ClickHouse via MCP server for efficient querying
    and analysis, leveraging AI models for enhanced insights.
    """

    server: MCPServerStdio | None
    env: Dict[str, str]
    agent: Agent[ClickHouseDependencies, ClickHouseOutput] | None

    def __init__(
        self,
        instructions: str = "You are a ClickHouse database analyst. Use the available MCP tools to query ClickHouse databases and provide insightful analysis. Be precise and include relevant data to support your analysis. Don't get too technical keep it seo friendly. When structuring analytical queries for the mcp server always mind the complexity and performance. Provide actionable insights and recommendations based on the data. MUST!!! MAKE SURE NOT TO OVERLOAD THE SERVER WITH COMPLEX QUERIES. ALWAYS OPTIMIZE FOR PERFORMANCE AND COST. ALWAYS KEEP IT MINIMAL BUT MEANINGFUL NOT A LOT OF QUERIES TO THE SERVER.",
        retries: int = 3,
        output_retries: int = 3,
    ):
        from .config import config

        selected_provider = config.model_provider

        api_key_attr = f"{selected_provider.upper()}_API_KEY"
        model_api_key = getattr(config.model_api, api_key_attr, None)

        # Only set the environment variable if we actually have a key.
        # Avoid overwriting an existing env var and skip None values to
        # keep default instantiation working in tests and minimal setups.
        if model_api_key:
            os.environ.setdefault(api_key_attr, model_api_key)

        # Set up environment for MCP server
        self.env = {
            "CLICKHOUSE_HOST": config.clickhouse_host,
            "CLICKHOUSE_PORT": config.clickhouse_port,
            "CLICKHOUSE_USER": config.clickhouse_user,
            "CLICKHOUSE_PASSWORD": config.clickhouse_password,
            "CLICKHOUSE_SECURE": config.clickhouse_secure,
        }
        # Defer heavy initialization (model provider may require API keys).
        self.server = None
        self.agent = None
        self._instructions = instructions
        self._retries = retries
        self._output_retries = output_retries

    def _ensure_agent(self) -> None:
        """Lazy-initialize MCP server and Agent to avoid requiring API keys at import/instantiation time."""
        if self.agent is not None and self.server is not None:
            return

        from .config import config

        # Initialize MCP server and agent when first needed
        self.server = MCPServerStdio(
            "mcp-clickhouse",
            args=[],
            env=self.env,
            process_tool_call=self.process_tool_call,
        )

        self.agent = Agent[ClickHouseDependencies, ClickHouseOutput](
            model=config.ai_model,
            deps_type=ClickHouseDependencies,
            output_type=ClickHouseOutput,
            toolsets=[self.server],
            instructions=self._instructions,
            retries=self._retries,
            output_retries=self._output_retries,
        )

    async def useHistoryProcessor(self, message_history: Optional[List[ModelMessage]] = None) -> List[ModelMessage]:
        from .config import config
        from .history_processor import history_processor

        total_tokens = 0

        for m in message_history if message_history else []:
            if hasattr(m, "usage"):
                total_tokens += m.usage.total_tokens

        # Ensure we always pass a concrete list to the processor
        concrete_history: List[ModelMessage] = message_history or []
        return await history_processor(total_tokens, concrete_history, config.model_provider)

    def getClickhouseParams(self) -> Dict[str, str]:
        return dict(
            host=self.env["CLICKHOUSE_HOST"],
            port=self.env["CLICKHOUSE_PORT"],
            user=self.env["CLICKHOUSE_USER"],
            password=self.env["CLICKHOUSE_PASSWORD"],
            secure=self.env["CLICKHOUSE_SECURE"],
        )

    def getClickhouseDeps(self, allowed_tables: Optional[List[str]] = None) -> ClickHouseDependencies:
        """Build ClickHouseDependencies and set per-call allowed_tables.

        This implementation intentionally keeps `allowed_tables` per-call
        only: if provided here we assign it directly to the returned deps
        object without attempting to merge with any agent-level default.
        """
        # Build explicitly so mypy can validate field names/types
        deps = ClickHouseDependencies(
            host=self.env["CLICKHOUSE_HOST"],
            port=self.env["CLICKHOUSE_PORT"],
            user=self.env["CLICKHOUSE_USER"],
            password=self.env["CLICKHOUSE_PASSWORD"],
            secure=self.env["CLICKHOUSE_SECURE"],
        )

        # Assign per-call allow-list directly (no merge/dedupe).
        if allowed_tables is not None:
            deps.allowed_tables = allowed_tables

        return deps

    async def run(
        self,
        allowed_tables: Optional[List[str]] = None,
        message_history: Optional[List[ModelMessage]] = None,
        query: str = "SHOW_TABLES",
    ) -> RunResult:
        try:
            # Ensure lazy init occurs here to avoid API key requirements during simple instantiation.
            self._ensure_agent()
            assert self.agent is not None
            message_history = await self.useHistoryProcessor(message_history)
            deps = self.getClickhouseDeps(allowed_tables=allowed_tables)
            agent = self.agent
            async with agent:
                result = await agent.run(
                    query,
                    deps=deps,
                    message_history=message_history,
                )
                all_messages = result.all_messages()
                new_messages = result.new_messages()
                usage = result.usage()
                output = result.output
            return RunResult(
                messages=all_messages,
                last_message=all_messages[-1] if all_messages else None,
                new_messages=new_messages,
                usage=usage,
                analysis=output.analysis,
                confidence=output.confidence,
            )
        except Exception as e:
            logger.error(f"MCP agent execution failed: {e}")
            if "TaskGroup" in str(e):
                raise Exception(
                    "MCP server connection failed. This might be due to network issues or UV environment conflicts."
                )
            raise Exception("MCP agent execution failed.")

    async def process_tool_call(
        self,
        ctx: RunContext[Any],
        call_tool_func: CallToolFunc,
        tool_name: str,
        tool_args: Dict[str, Any],
    ) -> Any:
        allowed_tables = ctx.deps.allowed_tables if ctx.deps else None

        # if allowed tables have length 0 we return empty list
        if allowed_tables is not None and len(allowed_tables) == 0:
            return []

        if tool_name == "list_tables":
            db = tool_args.get("database")
            if not isinstance(db, str):
                return []
            if not isinstance(allowed_tables, list) or not all(isinstance(x, str) for x in allowed_tables):
                # Fallback to single call if allow-list is not a proper list of strings
                return await call_tool_func(tool_name, tool_args, None)
            return await self.list_tables_multi(
                call_tool_func,
                database=db,
                allowed_tables=allowed_tables,
            )

        logger.info("Tool name: %s", tool_name)
        logger.info("tool_args: %s", tool_args)

        result = await call_tool_func(tool_name, tool_args, None)

        logger.info("ProcessToolCallback result: %s", result)
        return result

    async def list_tables_multi(
        self,
        call_tool_func: CallToolFunc,
        database: str,
        allowed_tables: List[str],
    ) -> List[Dict[str, Any]]:
        # Build tasks: one call per allowed table/pattern
        tasks = [call_tool_func("list_tables", {"database": database, "like": pat}, None) for pat in allowed_tables]

        # Run all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Merge + de-dupe by (db, name)
        seen: set[tuple[Any, Any]] = set()
        merged: List[Dict[str, Any]] = []
        for batch in results:
            # Only handle list batches
            if not isinstance(batch, list):
                continue
            for r in batch:
                if not isinstance(r, dict):
                    continue
                key = (r.get("database"), r.get("name"))
                if key in seen:
                    continue
                seen.add(key)
                merged.append(r)

        return merged
