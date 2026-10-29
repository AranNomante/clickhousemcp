# ClickHouse MCP Agent
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/clickhouse-mcp-agent?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/clickhouse-mcp-agent)
[![PyPI](https://img.shields.io/pypi/v/clickhouse-mcp-agent)](https://pypi.org/project/clickhouse-mcp-agent/)
[![pydantic-ai-slim](https://img.shields.io/badge/pydantic--ai--slim-1.96.1-blue)](https://pypi.org/project/pydantic-ai-slim/)
[![mcp-clickhouse](https://img.shields.io/badge/mcp--clickhouse-0.4.0-blue)](https://pypi.org/project/mcp-clickhouse/)

AI agent for ClickHouse database analysis via MCP (Model Context Protocol).

A single MCP server (`mcp-clickhouse`) driven by a single agent instance. You can scope what the agent discovers per call with allow-lists (`allowed_tables`, `allowed_databases`). See [Security](#security) for what they do and do not restrict.

## Features

- Query ClickHouse databases using natural language with AI models
- Structured output: `analysis`, `confidence`, `sql_used`
- Easy connection management (predefined or custom)
- Conversational context with message-history pruning/summarization
- No CLI or external .env required — configure at runtime
- Per-call discovery scoping via allow-lists (`allowed_tables`, `allowed_databases`)
- Read-only queries by default (enforced by `mcp-clickhouse`)
- Streamable results via `run_stream()`
- Persistent MCP server mode via `async with ClickHouseAgent()`
- Parallel queries via `run_batch()`
- Lifecycle reset via `reset()`
- Query result cache via `enable_cache=True`
- Typed exception hierarchy for reliable error handling
- Optional `structlog` integration (`pip install ".[logging]"`)

### Supported Providers

| Provider | Key env var | Notes |
|---|---|---|
| Google Gemini | `GOOGLE_API_KEY` | Default |
| OpenAI | `OPENAI_API_KEY` | |
| Anthropic | `ANTHROPIC_API_KEY` | |
| Grok (xAI) | `XAI_API_KEY` | Model prefix `xai:` (e.g. `xai:grok-4`) |
| Groq | `GROQ_API_KEY` | Fast open models (e.g. `groq:llama-3.3-70b-versatile`), free tier |
| Mistral | `MISTRAL_API_KEY` | |
| Cohere | `CO_API_KEY` | |

## Local Development (Docker)

The fastest way to get started — no cloud ClickHouse account needed:

```bash
# Start ClickHouse with seeded demo data (orders + products)
docker compose up -d

# Install the package with dev dependencies
pip install -e ".[dev]"

# Run the examples (set your Google API key first)
GOOGLE_API_KEY=... python examples/example_minimal.py
GOOGLE_API_KEY=... python examples/example_stream.py
GOOGLE_API_KEY=... python examples/example_0_11.py
GOOGLE_API_KEY=... python examples/example_integration.py
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

### Parallel queries

```python
async with ClickHouseAgent() as agent:
    results = await agent.run_batch(
        ["how many orders?", "total revenue?", "top 5 products?"],
        allowed_databases=["demo"],
    )
    for r in results:
        print(r.analysis)
```

### Query result cache

```python
agent = ClickHouseAgent(enable_cache=True)
result = await agent.run(query="how many orders?", allowed_databases=["demo"])
# identical call returns instantly from cache (stateless queries only)
```

### Lifecycle reset

```python
agent = ClickHouseAgent()
await agent.run(query="...")
await agent.reset()          # tear down MCP subprocess
await agent.run(query="...")  # re-initializes on next call
```

### Switching providers

All providers use the same interface — just swap the model string and key:

```python
# Anthropic Claude 4
config.set_ai_model("anthropic:claude-sonnet-4-6")
config.set_model_api_key("anthropic", "your_key")

# Google Gemini
config.set_ai_model("google:gemini-3.1-flash-lite")
config.set_model_api_key("google", "your_key")

# Grok (xAI)
config.set_ai_model("xai:grok-4")
config.set_model_api_key("xai", "your_key")

# Groq (fast open models, free tier — good for testing)
config.set_ai_model("groq:llama-3.3-70b-versatile")
config.set_model_api_key("groq", "your_key")
```

## Security

**Queries are read-only.** `mcp-clickhouse` runs every query with ClickHouse's `readonly` setting unless `CLICKHOUSE_ALLOW_WRITE_ACCESS=true` is set for the server, so the agent cannot modify data.

**Allow-lists scope discovery; they are not an access control.** `allowed_databases` and `allowed_tables` filter what the `list_databases` and `list_tables` tools return, which keeps the model focused on the right tables. They do **not** inspect the SQL passed to `run_query`: a model that writes `SELECT * FROM other_db.other_table` directly can still read it.

**To restrict what can be read, use ClickHouse permissions.** Connect with a ClickHouse user that only has `SELECT` grants on the data the agent may see:

```sql
CREATE USER agent_reader IDENTIFIED BY '...';
GRANT SELECT ON demo.orders TO agent_reader;
GRANT SELECT ON demo.products TO agent_reader;
```

ClickHouse then rejects any query outside those grants, whatever SQL the model generates.

## Message History & Summarization

Pass `message_history` between calls for multi-turn conversations. When token usage exceeds `summarize_config.token_limit`, older messages are automatically summarized into a compact form by a separate summarizer agent.

```python
summarize_config.set_token_limit(10000)
summarize_config.set_ai_model("google:gemini-3.1-flash-lite")
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
- An AI provider API key (Google, OpenAI, Anthropic, Grok, Groq, Mistral, or Cohere)

All dependencies are managed via `pyproject.toml`.

## Roadmap

### ✅ Done (0.11.x)

- MCP integration via `pydantic_ai.mcp.MCPServerStdio`
- SQL generation/execution via MCP tools
- Schema inspection (databases/tables/columns)
- Config-driven connections (playground/local/custom)
- Discovery scoping via per-call allow-lists (`allowed_tables`, `allowed_databases`)
- Runtime provider/model selection and API key management
- Structured outputs (`ClickHouseOutput`) and `RunResult` with `sql_used`
- Message history pruning/summarization
- Streaming results via `run_stream()`
- Persistent MCP server via `async with ClickHouseAgent()`
- Typed exception hierarchy
- Local development via Docker (`docker compose up -d`)
- `ruff` linting, Python 3.13 support, CI hardened
- Async batch queries via `run_batch()`
- `reset()` for lifecycle control
- Query result cache (`enable_cache=True`)
- `structlog` optional dep (`pip install ".[logging]"`)

### ✅ 0.12 — Stable

- API locked — no breaking changes without a major version
- All known bugs resolved
- `py.typed` check added to CI
- `mypy agent/` added to CI matrix
- Updated to `mcp-clickhouse` 0.4.0; `list_databases` tool now enforced by `allowed_databases` allow-list
- Default model updated to `google:gemini-3.1-flash-lite`

### ✅ 0.12.1 — Fixes

- Allow-list filtering now works against real `mcp-clickhouse` responses (previously bypassed)
- Contract tests against the real `mcp-clickhouse` server, and live tests against ClickHouse in CI
- Grok (xAI) and Groq provider setup corrected

### 🚧 Next

- Migrate to pydantic-ai 2.x (`MCPToolset`) and `mcp-clickhouse` 0.7
- `role` and query timeout options (ClickHouse-enforced access control)

### 🔭 Post-1.0 — Future

- FastAPI standalone deployment option

## Contributing

Open an issue or pull request for features or fixes.
