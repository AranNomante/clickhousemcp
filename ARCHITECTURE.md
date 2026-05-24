
# Architecture Overview

This document describes the architecture of the ClickHouse MCP Agent library.

## Main Components

- `agent/config.py`: Runtime configuration for model/provider and ClickHouse. Exposes `EnvConfig` as `config`, plus connection presets and summarization config (`SummarizeAgentEnv` as `summarize_config`). No external `.env` required.
- `agent/clickhouse_agent.py`: Core agent that wires a single `pydantic_ai.Agent` to a single ClickHouse MCP server (`MCPServerStdio`), defines `ClickHouseDependencies`, `ClickHouseOutput`, and returns a structured `RunResult`.
- `agent/history_processor.py`: Message history processor that prunes/summarizes older messages based on token usage and `summarize_config`.
- `agent/__init__.py`: Public surface re-exporting the agent, configs, and history helpers.

## Query Flow

1. Configure model/provider/API key via `agent.config.config` and optionally set ClickHouse connection parameters.
2. Instantiate `ClickHouseAgent()`, which:
   - Reads provider/model from `config` and sets the provider API key into the environment (for the selected provider).
   - Constructs a single `MCPServerStdio("mcp-clickhouse", env=...)` using ClickHouse settings from `config`.
   - Creates a single `pydantic_ai.Agent` with `deps_type=ClickHouseDependencies`, `output_type=ClickHouseOutput`, and `toolsets=[server]`.
3. Call `agent.run(query=..., allowed_tables=..., message_history=...)`.
4. The agent invokes MCP tools to inspect schema and run SQL as needed; results flow back into a `ClickHouseOutput`.
5. A `RunResult` is returned with `analysis`, `confidence`, `usage`, and updated `messages/new_messages/last_message` (result is also streamable).
6. If history grows, `history_processor` may summarize earlier messages using the summarizer model specified in `summarize_config`.

## Patterns & Conventions

- **PydanticAI Agent**: Structured model IO with strongly-typed `deps` and `output`.
- **MCP Tooling**: ClickHouse operations are performed via a single MCP server toolset.
- **Runtime Config**: All provider/model/connection settings are configured at runtime (no static `.env` dependency).
- **Allow-lists**: Per-call `allowed_tables` constrains scope of access. This is the primary access-restriction mechanism rather than managing multiple API keys or multiple agents.
- **History Management**: Pluggable processor summarizes when token usage exceeds `summarize_config.token_limit`.
- **Type Safety**: Dataclasses and type hints across public interfaces.

## Extensibility

- Add new connection profiles in `agent/config.py` (`ClickHouseConnections`).
- Support new providers by extending `ModelAPIConfig` and the provider enum in `agent/clickhouse_agent.py`.
- Customize summarization by tuning `summarize_config` (model/provider/token limit).
- Extend output fields by modifying `ClickHouseOutput` and corresponding usage in the agent.

## Local Development Setup

A `docker-compose.yml` at the repo root starts a local ClickHouse instance for running examples without a cloud account:

```
docker-compose.yml          # ClickHouse service, port 8123 (HTTP), persisted volume
docker/
└── init.sql                # Seeds demo.orders + demo.products on first start
examples/
├── example_minimal.py      # run() against local Docker, any supported provider
└── example_stream.py       # run_stream() against local Docker, any supported provider
```

Connection settings for local Docker: `host=localhost`, `port=8123`, `user=default`, `password=""`, `secure=false`.

## Version

- Current library version: `0.9.0` (from `pyproject.toml`).

## License

MIT
