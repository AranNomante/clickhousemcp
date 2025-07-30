
# Changelog

## [0.3.1a0] - 2025-07-30

### Refactor: Pure library, runtime config, modular logging, and documentation overhaul

- Removed all environment variable and .env dependencies from agent code
- Refactored configuration to use runtime setter methods (no env_config.py)
- Removed CLI/demo code from main package; moved usage examples to `examples/example.py`
- Removed `agent/main.py` and deprecated CLI entry from `pyproject.toml`
- Modularized logging; added global log level setter
- Updated `agent/clickhouse_agent.py` to use new config and connection logic
- Updated `agent/config.py` for runtime config, type safety, and clear connection profiles
- Added `server_cache.py` for TTL-based MCP server caching
- Updated `tests/test_basic.py` for new config, connection, and output logic
- Overhauled `README.md`: new usage examples, output structure, requirements, and roadmap
- Added version badge to `README.md`
- Rewrote `ARCHITECTURE.md` to focus on architecture only (components, flow, patterns)
- Removed `INSTALL.md` and all deprecated documentation
- Updated `setup.sh` for dev dependencies
- Bumped version to 0.3.1a0 (alpha)
- **Closes #7** (remove env dependencies, pure library)
- **Closes #11** (documentation overhaul, roadmap update)