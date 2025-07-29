# Architecture

## File Structure

```text
clickhousemcp/
├── agent/
│   ├── __init__.py          # Public API exports
│   ├── clickhouse_agent.py  # Core MCP agent logic
│   ├── config.py           # Connection configurations  
│   ├── main.py             # High-level interface & CLI
│   └── env_config.py       # Environment handling (dotenv)
├── pyproject.toml          # Dependencies & packaging
├── setup.sh               # Interactive setup script
├── run.sh                 # Automated run script
├── clean.sh               # Environment cleanup script
├── .env.example           # Environment template
├── LICENSE                # MIT License
├── INSTALL.md             # Installation instructions
└── README.md              # Documentation
```

## Components

### Core Files

- **clickhouse_agent.py**: PydanticAI agent with MCP server integration
  - Handles API key management via temporary environment variables
  - Supports runtime connection configuration
  - MCP server stdio communication with toolsets integration
  
- **config.py**: Built-in connection configurations
  - ClickHouseConfig dataclass for dynamic connections
  - Predefined configs: playground, local, env
  - RBAC support through user credential passing

- **main.py**: High-level interface and CLI entry point
  - query_clickhouse() convenience function
  - CLI command registration via pyproject.toml
  - Simplified API with consistent parameter ordering

- **env_config.py**: Environment and configuration management
  - Automatic .env loading with python-dotenv
  - Configuration validation with proper type annotations
  - Structured logging setup

### Utility Scripts

- **setup.sh**: Virtual environment creation and dependency installation
- **run.sh**: Automated activation and execution
- **clean.sh**: Environment cleanup and reset

## Key Features

### 1. Dynamic Connection Management

- Runtime connection configuration via ClickHouseConfig
- No environment file dependencies required
- Support for different ClickHouse instances (playground, local, custom)

### 2. RBAC Support

- Pass different user credentials dynamically
- Per-query authentication without global state
- Secure credential handling

### 3. Flexible API Key Handling

- Environment variables (.env file)
- Direct parameter passing to functions (model_api_key parameter)
- Temporary environment variable management with automatic cleanup

### 4. MCP Integration

- PydanticAI agent with ClickHouse MCP server
- Stdio transport for tool communication via toolsets
- Automatic server lifecycle management with async context managers

## Dependency Management

Everything is handled by `pyproject.toml`:

- UV package manager (automatically installed)
- MCP ClickHouse server (fastmcp-clickhouse)
- PydanticAI with Google AI integration
- Python-dotenv for environment loading
- All AI and database dependencies

## Configuration Options

### 1. Environment Variables (Traditional)

```bash
cp .env.example .env    # One-time setup
# Edit .env with GOOGLE_API_KEY
```

### 2. Direct Parameter Passing (Dynamic)

```python
# No environment setup needed
result = await query_clickhouse(
    query="SELECT 1",
    connection=ClickHouseConfig(...),
    model="gemini-2.0-flash",
    api_key="your-key-here"
)
```

## Architecture Patterns

- **Agent Pattern**: PydanticAI agent for structured AI interactions
- **MCP Protocol**: Model Context Protocol for tool integration via toolsets
- **Dependency Injection**: Runtime configuration via dataclasses
- **Factory Pattern**: Connection configuration factory methods
- **Type Safety**: Full mypy compliance with proper type annotations
