
# Architecture Overview

This document describes the architecture of the ClickHouse MCP Agent library.

## Main Components

- `agent/exceptions.py`: Typed exception hierarchy — `ClickHouseMCPError` (base), `MCPConnectionError`, `AgentExecutionError`, `HistoryProcessorError`.
- `agent/config.py`: Runtime configuration for model/provider and ClickHouse. Exposes `EnvConfig` as `config`, connection presets (`ClickHouseConnections`), and summarization config (`SummarizeAgentEnv` as `summarize_config`). No external `.env` required.
- `agent/clickhouse_agent.py`: Core agent — wires a single `pydantic_ai.Agent` to a single ClickHouse MCP server (`MCPServerStdio`). Defines `ClickHouseDependencies`, `ClickHouseOutput`, and `RunResult`. Handles allow-list enforcement, SQL capture, and persistent-server lifecycle.
- `agent/default_instruction.py`: Default system prompt. Instructs the agent to prefer application databases (`demo`, `default`) and skip system databases unless asked.
- `agent/history_processor.py`: Prunes/summarizes message history when token usage exceeds `summarize_config.token_limit`.
- `agent/__init__.py`: Public surface — re-exports agent, configs, history helpers, exceptions, and output types.

## Query Flow

1. Configure model/provider/API key via `agent.config.config` and optionally set ClickHouse connection parameters.
2. Instantiate `ClickHouseAgent()`, which:
   - Reads provider/model from `config` and sets the provider API key into the environment.
   - Lazily constructs `MCPServerStdio("mcp-clickhouse", env=...)` and a `pydantic_ai.Agent` on first use.
3. Call `agent.run(query=..., allowed_tables=..., allowed_databases=..., message_history=...)`:
   - If running outside a context manager: wraps the call in `async with agent:` (MCP server starts and stops each time).
   - If running inside `async with ClickHouseAgent() as agent:`: server is already running; call goes directly to `agent.run()`.
   - For parallel queries use `agent.run_batch(queries, ...)` which creates an asyncio task per query.
4. `process_tool_call` intercepts every MCP tool call:
   - `allowed_tables=[]` → blocks all calls immediately.
   - `allowed_databases` set → any `list_tables` call for an unlisted database returns empty.
   - `list_tables` with `allowed_tables` patterns → fans out one call per pattern via `list_tables_multi`, deduplicates results.
   - Any tool with a `query` argument → SQL is appended to the per-call `_sql_used_var` contextvar list (isolated per asyncio task).
5. The agent invokes MCP tools to inspect schema and execute SQL; results flow into a `ClickHouseOutput`.
6. A `RunResult` is returned with `analysis`, `confidence`, `sql_used`, `usage`, and updated `messages/new_messages/last_message`.
7. If history grows past `summarize_config.token_limit`, `history_processor` summarizes earlier messages using the summarizer model.

## Patterns & Conventions

- **PydanticAI Agent**: Structured model IO with strongly-typed `deps` (`ClickHouseDependencies`) and `output` (`ClickHouseOutput`).
- **MCP Tooling**: All ClickHouse operations go through a single MCP server toolset.
- **Runtime Config**: Provider/model/connection settings configured at runtime — no static `.env` dependency.
- **Allow-lists**: Per-call `allowed_tables` and `allowed_databases` constrain access scope without managing multiple API keys or agents.
- **SQL capture**: `RunResult.sql_used` is populated by intercepting tool call arguments via a `contextvars.ContextVar` — no prompt engineering required, safe for concurrent use.
- **Persistent server**: `async with ClickHouseAgent()` keeps the MCP subprocess alive across multiple `run()` / `run_batch()` calls; the one-shot pattern starts/stops per call.
- **Result cache**: `ClickHouseAgent(enable_cache=True)` caches stateless query results in an instance dict keyed by `(query, frozenset(tables), frozenset(databases))`.
- **Lifecycle reset**: `agent.reset()` tears down the agent and server state; next `run()` re-initializes lazily.
- **Typed errors**: All library errors inherit from `ClickHouseMCPError` — callers can catch at the base or at specific subtypes.
- **Type Safety**: Dataclasses, `py.typed`, and mypy across all public interfaces.

## Extensibility

- Add new connection profiles in `agent/config.py` (`ClickHouseConnections`).
- Support new providers by extending `ModelAPIConfig` with a new `<PROVIDER>_API_KEY` field.
- Customize summarization by tuning `summarize_config` (model/provider/token limit).
- Extend output fields by modifying `ClickHouseOutput` and the corresponding `RunResult`.

## File Layout

```
agent/
├── __init__.py             # Public re-exports
├── clickhouse_agent.py     # Core: ClickHouseAgent, RunResult, ClickHouseOutput, ClickHouseDependencies
├── config.py               # Global config singleton (EnvConfig), connection presets, SummarizeAgentEnv
├── default_instruction.py  # Default system prompt as a dataclass
├── exceptions.py           # Typed exception hierarchy
├── history_processor.py    # Token-aware summarization of message history
└── py.typed                # PEP 561 marker
```

## Local Development Setup

A `docker-compose.yml` at the repo root starts a local ClickHouse instance:

```
docker-compose.yml          # ClickHouse service, port 8123 (HTTP), persisted volume
docker/
└── init.sql                # Seeds demo.orders + demo.products on first start
examples/
├── example_minimal.py      # run() against local Docker, any supported provider
├── example_stream.py       # run_stream() against local Docker, any supported provider
└── example_0_11.py         # 0.11 feature showcase: reset(), run_batch(), cache, structlog
```

Connection settings for local Docker: `host=localhost`, `port=8123`, `user=default`, `password=""`, `secure=false`.

## Version

- Current library version: `0.11.2` (from `pyproject.toml`).

## License

MIT
