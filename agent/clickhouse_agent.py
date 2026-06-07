"""ClickHouse support agent that combines PydanticAI with ClickHouse MCP server.

This agent uses a similar pattern to the bank support example but integrates
with ClickHouse via MCP server for database queries.
"""

import asyncio
import contextvars
import logging
import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.mcp import CallToolFunc, MCPServerStdio, RunContext
from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import RunUsage

from agent.default_instruction import DefaultInstructions
from agent.exceptions import AgentExecutionError, MCPConnectionError

try:
    import structlog  # type: ignore[import-not-found]

    logger = structlog.get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)  # type: ignore[assignment]

# Per-task SQL accumulator — set at the start of each run() call so concurrent
# runs on the same agent instance each track their own SQL independently.
_sql_used_var: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar("_sql_used", default=None)


@dataclass
class ClickHouseDependencies:
    """Dependencies for ClickHouse connection and MCP server configuration."""

    host: str
    port: str
    user: str
    password: str = ""
    secure: bool = True
    allowed_tables: list[str] | None = None
    allowed_databases: list[str] | None = None


@dataclass
class ClickHouseOutput:
    """Output structure for ClickHouse agent responses."""

    analysis: str
    confidence: int


@dataclass
class RunResult:
    """Result structure for agent run method."""

    messages: list[ModelMessage]
    new_messages: list[ModelMessage]
    usage: RunUsage
    analysis: str
    confidence: int
    sql_used: list[str] = field(default_factory=list)
    last_message: ModelMessage | None = None


class ClickHouseAgent:
    """
    ClickHouse MCP Agent that uses PydanticAI for database queries.

    Supports both one-shot calls (MCP server starts/stops per run) and persistent
    server mode via ``async with ClickHouseAgent() as agent:``.
    """

    server: MCPServerStdio | None
    env: dict[str, str]
    agent: Agent[ClickHouseDependencies, ClickHouseOutput] | None
    _in_context: bool
    _sql_used: list[str]
    _cache: dict[tuple[str, frozenset[str] | None, frozenset[str] | None], "RunResult"]
    _enable_cache: bool

    def __init__(
        self,
        instructions: str | None = None,
        retries: int = 3,
        output_retries: int = 3,
        enable_cache: bool = False,
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
        self._in_context = False
        self._sql_used = []
        self._cache = {}
        self._enable_cache = enable_cache
        self._instructions = instructions
        self._retries = retries
        self._output_retries = output_retries

    def _ensure_agent(self) -> None:
        """Lazy-initialize MCP server and Agent to avoid requiring API keys at import/instantiation time."""
        if self.agent is not None and self.server is not None:
            return

        from .config import config

        model: Any = config.ai_model

        # Initialize MCP server and agent when first needed
        # MCPServerStdio is deprecated in pydantic-ai 1.102+ but the replacement
        # (MCPToolset + StdioTransport) requires fastmcp>=2.14 which conflicts with
        # mcp-clickhouse's fastmcp constraint. Revisit when mcp-clickhouse upgrades.
        self.server = MCPServerStdio(  # type: ignore[deprecated]
            "mcp-clickhouse",
            args=[],
            env=self.env,
            process_tool_call=self.process_tool_call,
        )

        if self._instructions is None:
            self._instructions = DefaultInstructions().instructions

        server = self.server  # narrow from MCPServerStdio | None
        self.agent = Agent[ClickHouseDependencies, ClickHouseOutput](  # type: ignore[call-overload]
            model=model,
            deps_type=ClickHouseDependencies,
            output_type=ClickHouseOutput,
            toolsets=[server],
            instructions=self._instructions,
            tool_retries=self._retries,
            output_retries=self._output_retries,
        )

    async def __aenter__(self) -> "ClickHouseAgent":
        """Enter persistent-server mode: MCP subprocess starts once and stays running."""
        self._ensure_agent()
        if self.agent is None:
            raise MCPConnectionError("Agent failed to initialize.")
        await self.agent.__aenter__()
        self._in_context = True
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit persistent-server mode and shut down the MCP subprocess."""
        if self.agent is not None:
            await self.agent.__aexit__(*args)
        self._in_context = False
        self.server = None
        self.agent = None

    async def reset(self) -> None:
        """Tear down and reset the agent so the next run() re-initializes from scratch.

        Safe to call outside a context manager. In persistent-server mode, exit the
        ``async with`` block instead — ``reset()`` is intended for one-shot usage.
        """
        if self.agent is not None:
            try:
                await self.agent.__aexit__(None, None, None)
            except Exception:
                pass
        self.server = None
        self.agent = None
        self._in_context = False
        self._sql_used = []
        self._cache = {}

    async def _use_history_processor(self, message_history: list[ModelMessage] | None = None) -> list[ModelMessage]:
        from .config import config
        from .history_processor import history_processor

        total_tokens = 0

        for m in message_history if message_history else []:
            if hasattr(m, "usage"):
                total_tokens += m.usage.total_tokens

        # Ensure we always pass a concrete list to the processor
        concrete_history: list[ModelMessage] = message_history or []
        return await history_processor(total_tokens, concrete_history, config.model_provider)

    def _get_clickhouse_params(self) -> dict[str, str]:
        return dict(
            host=self.env["CLICKHOUSE_HOST"],
            port=self.env["CLICKHOUSE_PORT"],
            user=self.env["CLICKHOUSE_USER"],
            password=self.env["CLICKHOUSE_PASSWORD"],
            secure=self.env["CLICKHOUSE_SECURE"],
        )

    def _get_clickhouse_deps(
        self,
        allowed_tables: list[str] | None = None,
        allowed_databases: list[str] | None = None,
    ) -> ClickHouseDependencies:
        """Build ClickHouseDependencies and set per-call allowed_tables and allowed_databases.

        allowed_tables=[] blocks all table-listing tool calls.
        allowed_databases=[] blocks all databases (returns empty for every list_tables call).
        Pass None for unrestricted access.
        """
        deps = ClickHouseDependencies(
            host=self.env["CLICKHOUSE_HOST"],
            port=self.env["CLICKHOUSE_PORT"],
            user=self.env["CLICKHOUSE_USER"],
            password=self.env["CLICKHOUSE_PASSWORD"],
            secure=self.env["CLICKHOUSE_SECURE"].lower() == "true",
        )

        # Assign per-call allow-lists directly (no merge/dedupe).
        if allowed_tables is not None:
            deps.allowed_tables = allowed_tables
        if allowed_databases is not None:
            deps.allowed_databases = allowed_databases

        return deps

    def _make_cache_key(
        self,
        query: str,
        allowed_tables: list[str] | None,
        allowed_databases: list[str] | None,
    ) -> tuple[str, frozenset[str] | None, frozenset[str] | None]:
        return (
            query,
            frozenset(allowed_tables) if allowed_tables is not None else None,
            frozenset(allowed_databases) if allowed_databases is not None else None,
        )

    async def run(
        self,
        allowed_tables: list[str] | None = None,
        allowed_databases: list[str] | None = None,
        message_history: list[ModelMessage] | None = None,
        query: str = "SHOW_TABLES",
    ) -> RunResult:
        # Cache lookup — only for stateless (no history) calls.
        # Capture now: _use_history_processor always returns a list (never None),
        # so we can't re-check message_history is None after calling it.
        is_stateless = message_history is None
        if self._enable_cache and is_stateless:
            cache_key = self._make_cache_key(query, allowed_tables, allowed_databases)
            if cache_key in self._cache:
                return self._cache[cache_key]

        try:
            self._ensure_agent()
            if self.agent is None:
                raise MCPConnectionError("Agent failed to initialize.")

            # Use a per-call list via contextvar so concurrent run() calls on the same
            # agent instance each track their own SQL without mixing.
            local_sql: list[str] = []
            token = _sql_used_var.set(local_sql)
            try:
                message_history = await self._use_history_processor(message_history)
                deps = self._get_clickhouse_deps(allowed_tables=allowed_tables, allowed_databases=allowed_databases)
                agent = self.agent
                if self._in_context:
                    # MCP server is already running — call directly without restarting it.
                    result = await agent.run(query, deps=deps, message_history=message_history)
                else:
                    async with agent:
                        result = await agent.run(query, deps=deps, message_history=message_history)
            finally:
                _sql_used_var.reset(token)
                self._sql_used = local_sql  # keep instance var updated for backward compat

            all_messages = result.all_messages()
            new_messages = result.new_messages()
            usage = result.usage
            output = result.output
            run_result = RunResult(
                messages=all_messages,
                last_message=all_messages[-1] if all_messages else None,
                new_messages=new_messages,
                usage=usage,
                analysis=output.analysis,
                confidence=output.confidence,
                sql_used=list(local_sql),
            )
            if self._enable_cache and is_stateless:
                self._cache[self._make_cache_key(query, allowed_tables, allowed_databases)] = run_result
            return run_result
        except (MCPConnectionError, AgentExecutionError):
            raise
        except Exception as e:
            logger.error("MCP agent execution failed: %s", e)
            if "TaskGroup" in str(e):
                raise MCPConnectionError(
                    "MCP server connection failed. This might be due to network issues or UV environment conflicts."
                ) from e
            raise AgentExecutionError("MCP agent execution failed.") from e

    async def run_batch(
        self,
        queries: list[str],
        *,
        allowed_tables: list[str] | None = None,
        allowed_databases: list[str] | None = None,
        message_history: list[ModelMessage] | None = None,
    ) -> list[RunResult]:
        """Run multiple queries concurrently against this agent.

        Each query executes in its own asyncio task with an independent SQL-tracking
        context, so ``RunResult.sql_used`` is correct per-query even under concurrency.

        Prefer using ``async with ClickHouseAgent() as agent:`` before calling
        ``run_batch()`` to keep the MCP subprocess alive across all queries.

        Raises the first exception encountered; partial results are discarded.
        """
        tasks = [
            asyncio.create_task(
                self.run(
                    query=q,
                    allowed_tables=allowed_tables,
                    allowed_databases=allowed_databases,
                    message_history=message_history,
                )
            )
            for q in queries
        ]
        try:
            return list(await asyncio.gather(*tasks))
        except Exception:
            for t in tasks:
                t.cancel()
            raise

    async def run_stream(
        self,
        allowed_tables: list[str] | None = None,
        allowed_databases: list[str] | None = None,
        message_history: list[ModelMessage] | None = None,
        query: str = "SHOW_TABLES",
    ) -> AsyncGenerator[Any, None]:
        # MCPServerStdio uses reference counting in __aenter__/__aexit__, so entering
        # agent.iter() while already inside `async with agent:` is safe — no double-start.
        try:
            self._ensure_agent()
            if self.agent is None:
                raise MCPConnectionError("Agent failed to initialize.")

            local_sql: list[str] = []
            token = _sql_used_var.set(local_sql)
            try:
                message_history = await self._use_history_processor(message_history)
                deps = self._get_clickhouse_deps(allowed_tables=allowed_tables, allowed_databases=allowed_databases)
                agent = self.agent

                async with agent.iter(
                    query,
                    deps=deps,
                    message_history=message_history,
                ) as agent_run:
                    async for node in agent_run:
                        yield node
            finally:
                _sql_used_var.reset(token)
                self._sql_used = local_sql

        except (MCPConnectionError, AgentExecutionError):
            raise
        except Exception as e:
            logger.error("MCP agent execution failed: %s", e)
            if "TaskGroup" in str(e):
                raise MCPConnectionError(
                    "MCP server connection failed. This might be due to network issues or UV environment conflicts."
                ) from e
            raise AgentExecutionError("MCP agent execution failed.") from e

    async def process_tool_call(
        self,
        ctx: RunContext[Any],
        call_tool_func: CallToolFunc,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> Any:
        allowed_tables = ctx.deps.allowed_tables if ctx.deps else None
        allowed_databases = ctx.deps.allowed_databases if ctx.deps else None

        # allowed_tables=[] explicitly blocks all tool calls (returns empty result immediately).
        # Pass allowed_tables=None to allow unrestricted access.
        if allowed_tables is not None and len(allowed_tables) == 0:
            return []

        if tool_name == "list_databases":
            if allowed_databases is not None and len(allowed_databases) == 0:
                return []
            result = await call_tool_func(tool_name, tool_args, None)
            if allowed_databases is not None and isinstance(result, list):
                return [db for db in result if isinstance(db, str) and db in allowed_databases]
            return result

        if tool_name == "list_tables":
            db = tool_args.get("database")
            if not isinstance(db, str):
                return []
            # Block databases not in the allow-list.
            if allowed_databases is not None and db not in allowed_databases:
                return []
            if not isinstance(allowed_tables, list) or not all(isinstance(x, str) for x in allowed_tables):
                # Fallback to single call if allow-list is not a proper list of strings
                return await call_tool_func(tool_name, tool_args, None)
            return await self.list_tables_multi(
                call_tool_func,
                database=db,
                allowed_tables=allowed_tables,
            )

        # Capture SQL from query tool calls for RunResult.sql_used.
        # Prefer the per-call contextvar list (set by run()/run_stream()); fall back to
        # the instance attribute so direct test calls still work.
        query_arg = tool_args.get("query")
        if isinstance(query_arg, str):
            sql_list = _sql_used_var.get(None)
            if sql_list is not None:
                sql_list.append(query_arg)
            else:
                self._sql_used.append(query_arg)

        result = await call_tool_func(tool_name, tool_args, None)

        return result

    async def list_tables_multi(
        self,
        call_tool_func: CallToolFunc,
        database: str,
        allowed_tables: list[str],
    ) -> list[dict[str, Any]]:
        # Build tasks: one call per allowed table/pattern
        tasks = [call_tool_func("list_tables", {"database": database, "like": pat}, None) for pat in allowed_tables]

        # Run all concurrently; keep going even if one pattern fails
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge + de-dupe by (db, name)
        seen: set[tuple[Any, Any]] = set()
        merged: list[dict[str, Any]] = []
        for batch in results:
            if isinstance(batch, BaseException):
                logger.warning("list_tables call failed for one pattern: %s", batch)
                continue
            # mcp-clickhouse returns {"tables": [...], ...}; fall back to raw list for compat
            if isinstance(batch, dict):
                batch = batch.get("tables", [])
            if not isinstance(batch, list):
                continue
            for r in batch:
                if not isinstance(r, dict):
                    continue
                db, name = r.get("database"), r.get("name")
                if not isinstance(db, str) or not isinstance(name, str):
                    continue
                key = (db, name)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(r)

        return merged
