# ClickHouse MCP Agent

A PydanticAI agent that integrates with ClickHouse databases using the Model Context Protocol (MCP).

## Features

- MCP-based ClickHouse integration with secure database access
- Structured output with natural language analysis and SQL transparency
- Flexible connection management for different ClickHouse instances
- Built-in configurations for common scenarios

## Installation

```bash
./setup.sh               # Setup virtual environment and install
cp .env.example .env      # Configure environment
# Edit .env with your GOOGLE_API_KEY
```

## Run

```bash
./run.sh                 # Activate environment and run project
```

## Usage

### Basic Query

```python
from agent import query_clickhouse

result = await query_clickhouse(
    query="What are the top 5 GitHub repositories by stars?",
    connection="playground"
)
print(f"Analysis: {result.analysis}")
```

### Custom Connection

```python
from agent import ClickHouseConfig

config = ClickHouseConfig(
    name="production",
    host="clickhouse.company.com",
    port="8443",
    user="analyst",
    password="secret"
)

result = await query_clickhouse(query="SHOW TABLES", connection=config)
```

### Current Usage (Library Import)

```python
# When installed as a library: pip install clickhouse-mcp-agent
from agent import query_clickhouse, ClickHouseConfig

# Basic usage
result = await query_clickhouse("SHOW DATABASES", "playground")

# RBAC with dynamic user credentials (already supported)
user_config = ClickHouseConfig(
    name="user_session",
    host="clickhouse.company.com",
    user="analyst_jane",
    password="jane_specific_password"
)
result = await query_clickhouse("SELECT * FROM user_logs", user_config)

# Completely dynamic 
result = await query_clickhouse(
    query="SHOW TABLES",
    connection=ClickHouseConfig(
        name="runtime",
        host="dynamic.clickhouse.com",
        user="runtime_user",
        password="runtime_pass"
    ),
    model="gemini-1.5-flash",
    api_key="your-google-api-key-here" 
)
```

### Environment Variables

The project automatically loads from `.env` file:

```python
result = await query_clickhouse(query="SELECT 1", connection="env")
```

## Built-in Connections

- `playground`: ClickHouse SQL playground (public demo data)
- `local`: Local instance (localhost:9000)
- `env`: From environment variables

## CLI

```bash
./run.sh                         # Automated run script
# OR manually:
source .venv/bin/activate
clickhouse-mcp-demo             # CLI command from pyproject.toml
python -m agent.main            # Direct module execution
```

## Output

Returns `ClickHouseOutput` with:

- `analysis`: Natural language results with SQL queries mentioned in the response

## Requirements

- Python 3.10+
- AI API key (Google/Gemini) - can be set via environment variable, .env file, or passed directly to the function

All other dependencies (UV, MCP servers, etc.) are handled automatically by pyproject.toml.

## Roadmap

### ✅ Completed Features

- [x] **MCP Integration**: PydanticAI + ClickHouse MCP server integration
- [x] **Query Execution**: SQL query execution via MCP tools
- [x] **Schema Inspection**: Database, table, and column exploration
- [x] **Connection Management**: Multiple connection configurations (playground, local, env)
- [x] **RBAC Support**: Pass different user credentials dynamically via ClickHouseConfig
- [x] **Dynamic Connections**: Runtime connection configuration without environment dependencies
- [x] **Direct API Key Passing**: Pass AI API keys directly to functions without environment variables
- [x] **Structured Output**: ClickHouseOutput with analysis, SQL, and confidence
- [x] **CLI Interface**: Command-line tool via clickhouse-mcp-demo

### 🚧 Planned Features (Discussed)

#### Enhanced Conversation Support

- [ ] **Message History**: Add message_history parameter to query_clickhouse() for conversation continuity
- [ ] **Conversational Agent**: ConversationalClickHouseAgent class for persistent memory across queries

#### Model Support

- [ ] **Model Agnostic Support**: Support for different AI models beyond Gemini

---

### Contributing

Have ideas for new features? Found something missing?

1. Check existing issues/discussions
2. Open a feature request with use case details
3. Consider contributing via pull request

**Current Focus**: Message history integration and model agnostic support.
