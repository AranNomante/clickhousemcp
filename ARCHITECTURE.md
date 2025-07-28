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
├── .env.example           # Environment template
└── README.md              # Documentation
```

## Components

- **clickhouse_agent.py**: PydanticAI agent with MCP server integration
- **config.py**: Built-in connection configs (playground, local, env)
- **main.py**: Convenience functions and CLI entry point
- **env_config.py**: Automatic .env loading with python-dotenv

## Dependency Management

Everything is handled by `pyproject.toml`:

- UV package manager (automatically installed)
- MCP ClickHouse server (automatically available)
- Python-dotenv for environment loading
- All AI dependencies

## Configuration

Uses automatic .env loading:

```bash
cp .env.example .env    # One-time setup
# No manual exports needed - loaded automatically
```
