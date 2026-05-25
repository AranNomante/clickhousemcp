# ClickHouse MCP Agent

![version](https://img.shields.io/badge/version-0.10.0-blue)

AI agent for ClickHouse database analysis via MCP (Model Context Protocol).

A single MCP server (`mcp-clickhouse`) driven by a single agent instance. Access restriction is performed via explicit allow-lists you pass per call (`allowed_tables`, `allowed_databases`), rather than managing multiple keys or fan-out across multiple agents.

## Features

- Query ClickHouse databases using natural language with AI models
- Structured output: `analysis`, `confidence`, `sql_used`
- Easy connection management (predefined or custom)
- Conversational context with message-history pruning/summarization
- No CLI or external .env required — configure at runtime
- Access restriction via per-call allow-lists (`allowed_tables`, `allowed_databases`)
- Streamable results via `run_stream()`
- Persistent MCP server mode via `async with ClickHouseAgent()`
- Typed exception hierarchy for reliable error handling

### Supported Providers

- OpenAI
- Anthropic
- Google Gemini
- Groq
- Mistral
- Cohere

## Local Development (Docker)

The fastest way to get started — no cloud ClickHouse account needed:

```bash
# Start ClickHouse with seeded demo data (orders + products)
docker compose up -d

# Install the package with dev dependencies
pip install -e ".[dev]"

# Run the examples (set your API key first)
GOOGLE_API_KEY=... python examples/example_minimal.py
GOOGLE_API_KEY=... python examples/example_stream.py
```

The `docker/init.sql` file seeds `demo.orders` (25 orders, May 2026) and `demo.products` (10 products across Electronics, Sports, Home, Books) automatically on first start.

## Quickstart

```python
import asyncio
from agent.clickhouse_agent import ClickHouseAgent
from agent.config import config

config.set_ai_model("openai:gpt-4o-mini")
config.set_model_api_key("openai", "your_api_key_here")
config.set_clickhouse(host="localhost", port="8123", user="default", password="", secure="false")

async def main():
    agent = ClickHouseAgent()
    result = await agent.run(
        allowed_tables=["orders", "products"],
        allowed_databases=["demo"],
        query="give me some insights on the recent data",
    )
    print("Analysis:", result.analysis)
    print("Confidence:", result.confidence)
    print("SQL used:", result.sql_used)

asyncio.run(main())
```

### Persistent server (multiple queries)

Use the context manager to keep the MCP subprocess alive across calls — avoids subprocess startup overhead on every query:

```python
async def main():
    async with ClickHouseAgent() as agent:
        r1 = await agent.run(query="how many orders were placed last week?")
        r2 = await agent.run(query="which products are selling fastest?", message_history=r1.messages)
```

### Switching providers

All providers use the same interface — just swap the model string and key:

```python
# Anthropic
config.set_ai_model("anthropic:claude-haiku-4-5-20251001")
config.set_model_api_key("anthropic", "your_key")

# Google
config.set_ai_model("google-gla:gemini-2.0-flash")
config.set_model_api_key("google", "your_key")

# Groq
config.set_ai_model("groq:llama-3.3-70b-versatile")
config.set_model_api_key("groq", "your_key")
```

## Message History & Summarization

Pass `message_history` between calls for multi-turn conversations. When token usage exceeds `summarize_config.token_limit`, older messages are automatically summarized into a compact form by a separate summarizer agent.

```python
summarize_config.set_token_limit(10000)
summarize_config.set_ai_model("gemini-2.5-flash")
```

## Output

Each call to `ClickHouseAgent.run()` returns a `RunResult`:

| Field | Description |
|---|---|
| `analysis` | Natural-language result text from the model |
| `confidence` | Confidence level (1–10) |
| `sql_used` | List of SQL strings executed during the run |
| `messages` | Full (possibly pruned/summarized) message history |
| `new_messages` | Only messages created in the latest turn |
| `last_message` | The last message in the conversation |
| `usage` | Token/usage statistics for the run |

## Error Handling

All errors raise from a typed hierarchy so you can catch at the right level:

```python
from agent.exceptions import ClickHouseMCPError, MCPConnectionError, AgentExecutionError

try:
    result = await agent.run(query="...")
except MCPConnectionError:
    # MCP subprocess failed to start or connection dropped
    ...
except AgentExecutionError:
    # Agent logic failed during the run
    ...
except ClickHouseMCPError:
    # Any library error
    ...
```

## Requirements

- Python 3.10+
- AI API key for your provider (OpenAI, Anthropic, Google/Gemini, Groq, Mistral, Cohere)

All dependencies are managed via `pyproject.toml`.

## Roadmap

### ✅ Done

- MCP integration via `pydantic_ai.mcp.MCPServerStdio`
- SQL generation/execution via MCP tools
- Schema inspection (databases/tables/columns)
- Config-driven connections (playground/local/custom)
- Access restriction via per-call allow-lists (`allowed_tables`, `allowed_databases`)
- Runtime provider/model selection and API key management
- Structured outputs (`ClickHouseOutput`) and `RunResult` with `sql_used`
- Message history pruning/summarization
- Streaming results via `run_stream()`
- Persistent MCP server via `async with ClickHouseAgent()`
- Typed exception hierarchy
- Local development via Docker (`docker compose up -d`)
- `ruff` linting, Python 3.13 support, CI hardened

### ⚙️ 0.11 — Agent API expansion

- Async batch queries (parallel queries in one call)
- `ClickHouseAgent.reset()` for lifecycle control without re-instantiation
- `structlog` optional dep for structured observability
- `pydantic-ai` API audit and model ref updates (Claude 4 / GPT family)

### 🔒 0.12 — Stable

- API locked — no breaking changes without a major version
- All known bugs resolved
- `py.typed` check added to CI

### 🔭 Post-1.0 — Future

- Database-agnostic abstraction (Elasticsearch, MongoDB, Postgres)
- FastAPI standalone deployment option

## Contributing

Open an issue or pull request for features or fixes.
