# ClickHouse MCP Agent

![version](https://img.shields.io/badge/version-0.9.0-blue)

AI agent for ClickHouse database analysis via MCP (Model Context Protocol).

This release reflects a simplified architecture: a single MCP server
(`mcp-clickhouse`) driven by a single agent instance. Access restriction is
performed via explicit allow-lists you pass per call (databases/tables), rather
than managing multiple keys or fan-out across multiple agents.

## Features

- Query ClickHouse databases using AI models
- Structured output: analysis, confidence
- Easy connection management (predefined or custom)
- Conversational context with message-history pruning/summarization
- No CLI or external .env required; configure at runtime
- Single MCP server, single agent lifecycle (no multi-key fan-out)
- Access restriction via per-call allow-lists (`allowed_tables`)
- Streamable results

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
OPENAI_API_KEY=sk-... python examples/example_minimal.py
OPENAI_API_KEY=sk-... python examples/example_stream.py
```

The `docker/init.sql` file seeds `demo.orders` (25 orders, May 2026) and `demo.products` (10 products across Electronics, Sports, Home, Books) automatically on first start.

## Quickstart

- Set model/provider and API key using the runtime config
- Instantiate `ClickHouseAgent` and call `run()` or `run_stream()`

```py
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
        query="give me some insights on the recent data",
    )
    print("Analysis:", result.analysis)
    print("Confidence:", result.confidence)

asyncio.run(main())
```

### Switching providers

All providers use the same interface — just swap the model string and key:

```py
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

- For multi-turn conversations, pass `message_history` between calls. If token usage grows, the agent can summarize history (see below).

## Message History & Summarization

- History processing is handled in `agent/history_processor.py`.
- Summarization behavior is controlled via `agent.config.summarize_config` (model, provider, token limit).
- When token usage exceeds the configured limit, older messages are summarized into a compact form.

## Output

Each call to `ClickHouseAgent.run()` returns a `RunResult` with:

- `messages`: Full (possibly pruned/summarized) message history.
- `new_messages`: Only messages created in the latest turn.
- `last_message`: The last message in the conversation.
- `usage`: Token/usage statistics for the run.
- `analysis`: Natural-language result text from the model.
- `confidence`: Confidence level (1-10).

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
- Access restriction via per-call allow-lists (`allowed_tables`)
- Runtime provider/model selection and API key management
- Structured outputs (`ClickHouseOutput`) and `RunResult`
- Message history pruning/summarization
- Streaming results via `run_stream()`
- Local development via Docker (`docker compose up -d`)
- `ruff` linting, Python 3.13 support, CI hardened

### 🔨 0.10 — Production hardening

- Custom exception types (`MCPConnectionError`, `AgentExecutionError`)
- `sql_used` extraction from tool call results
- `allowed_databases` parameter alongside `allowed_tables`
- `async with ClickHouseAgent()` context manager
- Persistent MCP server across multiple `run()` calls
- Integration tests: allow-list, streaming, summarization, error paths

### ⚙️ 0.11 — Agent API expansion

- Async batch queries (parallel queries in one call)
- `ClickHouseAgent.reset()` for lifecycle control
- `structlog` optional dep for structured observability
- `pydantic-ai` API audit and model ref updates

### 🔒 0.12 — Stable

- API locked — no breaking changes without a major version
- All known bugs resolved

### 🔭 Post-1.0 — Future

- Database-agnostic abstraction (Elasticsearch, MongoDB, Postgres)
- FastAPI standalone deployment option

## Contributing

Open an issue or pull request for features or fixes.
