# ClickHouse MCP Agent

![version](https://img.shields.io/badge/version-0.3.1a0-blue)

AI agent for ClickHouse database analysis via MCP (Model Context Protocol).

## Features

- Query ClickHouse databases using AI models
- Structured output: analysis, SQL used, confidence
- Easy connection management (predefined or custom)
- No CLI or environment setup required

### Supported Providers

- OpenAI
- Anthropic
- Google Gemini
- Groq
- Mistral
- Cohere

## Usage

- Configure your model, API key, and connection using the runtime config API.
- Run queries using the `ClickHouseAgent`.
- Multi-model/provider support is automatic—just set the API key for each provider.

See the `examples/` directory for full, canonical usage scripts:

- `examples/example_minimal.py`: Minimal query
- `examples/example_switch_provider.py`: Switch provider/model at runtime
- `examples/example_error_handling.py`: Error handling for missing API key
- `examples/example_multi_query.py`: Multiple queries in a loop

All features and usage patterns are covered in these scripts.

## Output

Returns a `ClickHouseOutput` object:

- `analysis`: Natural language results with SQL queries
- `sql_used`: SQL query that was executed
- `confidence`: Confidence level (1-10)

## Requirements

- Python 3.10+
- AI API key for your chosen provider (OpenAI, Anthropic, Google/Gemini, Groq, Mistral, Cohere)

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
- [x] **Multi-Model Support**: Runtime selection of provider/model and API key management

### 🚧 Planned / In Progress

- [ ] **Message History**: Add message_history parameter for conversational context
- [ ] **Conversational Agent**: Persistent memory across queries
- [ ] **Improved Error Handling**: More robust error and exception management
- [ ] **Advanced Output Formatting**: Customizable output for downstream applications

---

## Contributing

Open an issue or pull request for features or fixes.
