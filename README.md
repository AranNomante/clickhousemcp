# ClickHouse MCP Agent

![version](https://img.shields.io/badge/version-0.7.0-blue)

AI agent for ClickHouse database analysis via MCP (Model Context Protocol).

This release reflects a simplified architecture: a single MCP server
(`mcp-clickhouse`) driven by a single agent instance. Access restriction is
performed via explicit allow-lists you pass per call (databases/tables), rather
than managing multiple keys or fan-out across multiple agents.

## Features

- Query ClickHouse databases using AI models
- Structured output: analysis, SQL used, confidence
- Easy connection management (predefined or custom)
- Conversational context with message-history pruning/summarization
- No CLI or external .env required; configure at runtime
- Single MCP server, single agent lifecycle (no multi-key fan-out)
- Access restriction via per-call allow-lists (`allowed_dbs`, `allowed_tables`)

### Supported Providers

- OpenAI
- Anthropic
- Google Gemini
- Groq
- Mistral
- Cohere

## Quickstart

- Set model/provider and API key using the runtime config
- Instantiate `ClickHouseAgent` and call `run()`

Example mirrors `examples/example_minimal.py`:

```py
import asyncio
from agent.clickhouse_agent import ClickHouseAgent
from agent.config import config

config.set_log_level("DEBUG")
config.set_ai_model("gemini-2.0-flash")
config.set_model_api_key("google", "your_api_key_here")

async def main():
    agent = ClickHouseAgent()
    # Single MCP server (mcp-clickhouse). Limit scope via allow-lists (recommended)
    result = await agent.run(
        allowed_tables=["top_repos_mv"],
        allowed_dbs=["github"],
        query="SHOW_TABLES",
    )
    print("Analysis:", result.analysis)
    print("SQL Used:", result.sql_used)
    print("Confidence:", result.confidence)

asyncio.run(main())
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
- `sql_used`: SQL used (if applicable) from the model output.
- `confidence`: Confidence level (1-10).

## Requirements

- Python 3.10+
- AI API key for your provider (OpenAI, Anthropic, Google/Gemini, Groq, Mistral, Cohere)

All dependencies are managed via `pyproject.toml`.

## Roadmap

### ✅ Completed

- MCP integration via `pydantic_ai.mcp.MCPServerStdio`
- SQL generation/execution via MCP tools
- Schema inspection (databases/tables/columns)
- Config-driven connections (playground/local/custom)
- Access restriction via per-call allow-lists (`allowed_dbs`/`allowed_tables`)
- Runtime provider/model selection and API key management
- Structured outputs (`ClickHouseOutput`) and `RunResult`
- Message history pruning/summarization
- Type annotations and basic linting

### 🚧 Planned

- Improved error handling and diagnostics
- Advanced output formatting for downstream apps

## Contributing

Open an issue or pull request for features or fixes.
