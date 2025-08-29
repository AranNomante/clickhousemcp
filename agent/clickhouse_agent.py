"""ClickHouse support agent that combines PydanticAI with ClickHouse MCP server.

This agent uses a similar pattern to the bank support example but integrates
with ClickHouse via MCP server for database queries.
"""

import os

from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio, RunContext, CallToolFunc
from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import Usage

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
    # Optional per-request or default allow-list for tables. If provided at
    # Optional per-request allow-list for tables. This value is intended to
    # be provided per-call (via `query(allowed_tables=...)`) and will not be
    # merged with any agent-level defaults. Keep semantics simple and
    # explicit per-request.
    allowed_tables: Optional[list[str]] = None
    allowed_dbs: Optional[list[str]] = None


@dataclass
class ClickHouseOutput:
    """Output structure for ClickHouse agent responses."""

    """Analysis of the query result."""
    analysis: str

    """Confidence level of the analysis (1-10)."""
    confidence: int

    """SQL query used to generate the result."""
    sql_used: Optional[str] = None


@dataclass
class RunResult:
    """Result structure for agent run method."""

    """Messages exchanged during the query."""
    messages: list[ModelMessage]

    """New messages added during the query execution."""
    new_messages: list[ModelMessage]

    usage: Usage

    """Analysis of the query result."""
    analysis: str

    """Confidence level of the analysis (1-10)."""
    confidence: int

    """SQL query used to generate the result."""
    sql_used: Optional[str] = None

    """Last message in the conversation, useful for context."""
    last_message: Optional[ModelMessage] = None


class ClickHouseAgent:
    """
    ClickHouse MCP Agent that uses PydanticAI for database queries.

    This agent integrates with ClickHouse via MCP server for efficient querying
    and analysis, leveraging AI models for enhanced insights.
    """

    server: MCPServerStdio
    env: dict
    agent: Agent

    def __init__(
        self,
        instructions: str = "You are a ClickHouse database analyst. Use the available MCP tools to query ClickHouse databases and provide insightful analysis. Always mention the SQL queries you used in your response. Be precise and include relevant data to support your analysis.",
        retries: int = 3,
        output_retries: int = 3,
    ):
        from .config import config

        selected_provider = config.model_provider

        api_key_attr = f"{selected_provider.upper()}_API_KEY"
        model_api_key = getattr(config.model_api, api_key_attr, None)

        os.environ[api_key_attr] = model_api_key

        # Set up environment for MCP server
        self.env = {
            "CLICKHOUSE_HOST": config.clickhouse_host,
            "CLICKHOUSE_PORT": config.clickhouse_port,
            "CLICKHOUSE_USER": config.clickhouse_user,
            "CLICKHOUSE_PASSWORD": config.clickhouse_password,
            "CLICKHOUSE_SECURE": config.clickhouse_secure,
        }

        self.server = MCPServerStdio("mcp-clickhouse", args=[], env=self.env, process_tool_call=self.process_tool_call)

        self.agent = Agent(
            model=config.ai_model,
            deps_type=ClickHouseDependencies,
            output_type=ClickHouseOutput,
            toolsets=[self.server],
            instructions=instructions,
            retries=retries,
            output_retries=output_retries,
        )

    async def useHistoryProcessor(self, message_history: Optional[list[ModelMessage]] = None):
        from .config import config
        from .history_processor import history_processor

        total_tokens = 0

        for m in message_history if message_history else []:
            if hasattr(m, "usage"):
                total_tokens += m.usage.total_tokens

        return await history_processor(total_tokens, message_history, config.model_provider)

    def getClickhouseParams(self):
        return dict(
            host=self.env["CLICKHOUSE_HOST"],
            port=self.env["CLICKHOUSE_PORT"],
            user=self.env["CLICKHOUSE_USER"],
            password=self.env["CLICKHOUSE_PASSWORD"],
            secure=self.env["CLICKHOUSE_SECURE"],
        )

    def getClickhouseDeps(self, allowed_tables: Optional[list[str]] = None, allowed_dbs: Optional[list[str]] = None):
        """Build ClickHouseDependencies and set per-call allowed_tables.

        This implementation intentionally keeps `allowed_tables` per-call
        only: if provided here we assign it directly to the returned deps
        object without attempting to merge with any agent-level default.
        """
        params = self.getClickhouseParams()
        deps = ClickHouseDependencies(**params)

        # Assign per-call allow-list directly (no merge/dedupe).
        if allowed_tables is not None:
            deps.allowed_tables = allowed_tables

        if allowed_dbs is not None:
            deps.allowed_dbs = allowed_dbs

        return deps

    async def run(
        self,
        allowed_tables: Optional[list[str]] = None,
        allowed_dbs: Optional[list[str]] = None,
        message_history: Optional[list[ModelMessage]] = None,
        query: str = "SHOW_TABLES",
    ):
        try:
            deps = self.getClickhouseDeps(allowed_tables=allowed_tables, allowed_dbs=allowed_dbs)
            async with self.agent:
                result = await self.agent.run(query, deps=deps, message_history=message_history)
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
                sql_used=output.sql_used,
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
        tool_args: dict[str, Any],
    ) -> Any:

        logger.debug("Process_tool_called with tool_name=%s, tool_args=%s, ctx=%s", tool_name, tool_args, ctx)

        # Inject allow-list access restrictions if provided on deps.
        try:
            deps = getattr(ctx, "deps", None)
            if deps is not None:
                allowed_tables = getattr(deps, "allowed_tables", None)
                allowed_dbs = getattr(deps, "allowed_dbs", None)
                # Only add fields if caller supplied them per request
                if allowed_tables is not None and "allowed_tables" not in tool_args:
                    tool_args = {**tool_args, "allowed_tables": allowed_tables}
                if allowed_dbs is not None and "allowed_dbs" not in tool_args:
                    tool_args = {**tool_args, "allowed_dbs": allowed_dbs}
        except Exception as inj_err:
            logger.debug("Allow-list injection skipped due to error: %s", inj_err)

        result = await call_tool_func(tool_name, tool_args, None)

        logger.debug("ProcessToolCallback result: %s", result)
        return result

    def tool_name_hook(self, name, allowed_tables: Optional[list[str]] = None, allowed_dbs: Optional[list[str]] = None):
        # TODO: to be implemented
        return
