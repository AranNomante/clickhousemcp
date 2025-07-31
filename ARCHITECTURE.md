
# Architecture Overview

This document describes the architecture of the ClickHouse MCP Agent library.

## Main Components

- `agent/config.py`: Runtime configuration for ClickHouse connections and AI model settings. No environment variable or .env dependency.
- `agent/clickhouse_agent.py`: Core agent logic for querying ClickHouse via MCP. Handles query, model invocation, and output.
- `agent/server_cache.py`: TTL-based cache for server connections.

## Query Flow

1. User provides a query (natural language request, e.g. "Show all databases available to the demo user") and (optionally) connection info.
2. Agent uses the selected AI model to analyze the query and generate the appropriate SQL for ClickHouse.
3. SQL is executed against ClickHouse via MCP.
4. Results are returned as a structured `ClickHouseOutput` object.

## Architecture Patterns

- **Agent Pattern**: PydanticAI agent for structured AI interactions
- **MCP Protocol**: Model Context Protocol for tool integration via toolsets
- **Dependency Injection**: Runtime configuration via dataclasses
- **Factory Pattern**: Connection configuration factory methods
- **Type Safety**: Full mypy compliance with proper type annotations

## Extensibility

- Add new connection profiles in `config.py`
- Support new AI models and providers by updating model selection logic
- Provider/model selection is runtime and supports multiple providers and API keys
- Extend output formatting as needed

## License

MIT
