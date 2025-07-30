# ClickHouse MCP Agent

![version](https://img.shields.io/badge/version-0.3.1a0-blue)

AI agent for ClickHouse database analysis via MCP (Model Context Protocol).

## Features

- Query ClickHouse databases using AI models
- Structured output: analysis, SQL used, confidence
- Easy connection management (predefined or custom)
- No CLI or environment setup required

## Usage

### Basic Example

```python
import asyncio
from agent.clickhouse_agent import ClickHouseAgent
from agent.config import config

# Set up model and logging (optional)
config.set_ai_model("gemini-2.0-flash")
config.set_log_level("INFO")

# Set connection defaults (optional)
config.set_clickhouse(host="sql-clickhouse.clickhouse.com", user="demo")

# The 'query' parameter is a natural language request from the user. The agent will analyze it and generate the appropriate SQL for ClickHouse.
async def run_query():
    agent = ClickHouseAgent()
    result = await agent.run(
        model_api_key="your_api_key_here",
        model=config.ai_model,
        query="Show all databases available to the demo user"
        # Uses config defaults for connection
    )
    print("Analysis:", result.analysis)
    print("SQL Used:", result.sql_used)
    print("Confidence:", result.confidence)

asyncio.run(run_query())
```

### Custom Connection Example

```python
from agent.clickhouse_agent import ClickHouseAgent
from agent.config import ClickHouseConnections

ch_config = ClickHouseConnections.get_config("playground")
agent = ClickHouseAgent()
result = await agent.run(
    model_api_key="your_api_key_here",
    model="gemini-2.0-flash",
    query="List all tables in the default database",
    host=ch_config.host,
    port=ch_config.port,
    user=ch_config.user,
    password=ch_config.password,
    secure=ch_config.secure,
)
print("Analysis:", result.analysis)
```

## Output

Returns a `ClickHouseOutput` object:

- `analysis`: Natural language results with SQL queries
- `sql_used`: SQL query that was executed
- `confidence`: Confidence level (1-10)

## Requirements

- Python 3.10+
- AI API key (Google/Gemini)


All dependencies are handled by `pyproject.toml`.

## Roadmap

### ✅ Completed Features

- [x] **MCP Integration**: PydanticAI + ClickHouse MCP server integration
- [x] **Query Execution**: SQL query generation and execution via MCP
- [x] **Schema Inspection**: Database, table, and column exploration
- [x] **Connection Management**: Multiple connection configurations (playground, custom)
- [x] **RBAC Support**: Per-query user credentials via config
- [x] **Dynamic Connections**: Runtime connection configuration, no environment dependencies
- [x] **Direct API Key Passing**: Pass AI API keys directly to agent (model_api_key)
- [x] **Structured Output**: ClickHouseOutput with analysis, SQL, and confidence
- [x] **Type Safety**: Full type annotations and mypy compliance
- [x] **Code Quality**: Black formatting, isort, flake8 linting

### 🚧 Planned / In Progress

- [ ] **Message History**: Add message_history parameter for conversational context
- [ ] **Conversational Agent**: Persistent memory across queries
- [ ] **Model Agnostic Support**: Support for additional AI models
- [ ] **Improved Error Handling**: More robust error and exception management
- [ ] **Advanced Output Formatting**: Customizable output for downstream applications

---

## Contributing

Open an issue or pull request for features or fixes.
