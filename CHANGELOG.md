
# Changelog

## [0.10.0] - 2026-05-25

### Fixed

- Dead floating string literals in `ClickHouseOutput` and `RunResult` replaced with proper class docstrings.
- `default_instruction.py` rewritten: agent now prefers application databases (`demo`, `default`) and skips system databases unless explicitly asked, fixing the "which database?" prompt.
- Internal methods renamed from camelCase to snake_case: `useHistoryProcessor` → `_use_history_processor`, `getClickhouseDeps` → `_get_clickhouse_deps`, `getClickhouseParams` → `_get_clickhouse_params`.
- Dead `ModelProvider` enum removed (was never wired in).
- `run_stream()` return type corrected: `AsyncIterator[Any]` → `AsyncGenerator[Any, None]`.
- `set_log_level()` no longer installs root logger handlers — libraries must not configure the root logger.
- `allowed_tables=[]` blocking behavior documented in `process_tool_call` comment.
- `ClickHouseDependencies.secure` changed from `str` to `bool`; string-to-bool conversion now happens at the MCP env boundary in `_get_clickhouse_deps()`.
- `assert self.agent is not None` replaced with an explicit `RuntimeError` guard in `run()` and `run_stream()`.
- `call_tool_func` calls updated to pass `None` as the required third argument (`extras`) matching the `CallToolFunc(str, dict, dict | None)` signature in pydantic-ai 1.96.x.
- `Agent` constructor annotated with `# type: ignore[call-overload]` to suppress the overload mismatch caused by the deprecated `MCPServerStdio` toolset type.

### Added

- `agent/exceptions.py`: custom exception hierarchy — `ClickHouseMCPError` (base), `MCPConnectionError`, `AgentExecutionError`, `HistoryProcessorError`. All bare `Exception` raises in `clickhouse_agent.py` and `history_processor.py` replaced with typed exceptions.
- `allowed_databases` parameter on `run()`, `run_stream()`, and `ClickHouseDependencies`. `process_tool_call` enforces it: any `list_tables` call for a database not in the allow-list returns an empty result immediately.
- `sql_used: list[str]` field on `RunResult`. Populated by `process_tool_call` whenever a tool call contains a `query` argument (i.e. a SQL-executing tool).
- `async with ClickHouseAgent() as agent:` context manager. Entering the context starts the MCP subprocess once; subsequent `run()` calls reuse the live connection. Exiting stops the subprocess cleanly.
- Persistent MCP server: when running inside the context manager, `run()` skips the per-call `async with agent:` overhead.
- Exceptions, `RunResult`, and all public types now exported from `agent/__init__.py`.
- `tests/test_integration.py`: 17 new tests covering exception hierarchy, `allowed_tables` enforcement, `allowed_databases` enforcement, `sql_used` capture, `_get_clickhouse_deps`, `RunResult` structure, context manager interface, and deprecation-warning guard for `_ensure_agent`.

---

## [0.9.0] - 2026-05-24

### Fixed

- Exception chaining: both `run()` and `run_stream()` now use `raise ... from e` so the original traceback is preserved instead of being swallowed.
- `summarize_config` is now exported from `agent/__init__.py` (was importable from `agent.config` but missing from the public surface).
- History processor now logs a `WARNING` (not just `INFO`) when summarization is skipped due to a provider mismatch, making the silent-skip footgun visible.

### Changed

- PyPI classifier corrected from `5 - Production/Stable` to `4 - Beta` (project is at 0.x).
- `uv` removed from runtime `dependencies` and from `[build-system] requires` — it is a developer tool, not a library runtime dependency.
- Linting/formatting toolchain replaced: `flake8` + `isort` + `black` → `ruff` (single tool, faster, covers all three). `[tool.black]` and `[tool.isort]` config sections removed.
- Python 3.13 added to classifiers and target matrix.
- Version bumped to `0.9.0`.

### Added

- `docker-compose.yml`: local ClickHouse service (port 8123, persisted volume, health check) for running examples without a cloud account.
- `docker/init.sql`: seeds `demo.orders` (25 orders, May 2026) and `demo.products` (10 products) on first container start.

### Docs

- `ARCHITECTURE.md`: removed phantom `allowed_dbs=` parameter from query-flow description; removed `sql_used` from `RunResult` field list (not yet implemented); added local development setup section.
- `README.md`: removed `result.sql_used` from quickstart example and output section; added Local Development (Docker) section; added provider-switching examples for Anthropic, Google, and Groq; updated roadmap with concrete planned features.
- `CLAUDE.md`: added Documentation Update Rule checklist; updated Key Files table; marked logging bug as fixed.
- `examples/example_minimal.py`: updated to use local Docker ClickHouse (`localhost:8123`), real table names (`orders`, `products`), API key from env var, `gpt-4o-mini`.
- `examples/example_stream.py`: same updates as `example_minimal.py`; fixed logging bug (`logger.info("received chunk %s", chunk)`).

## [0.8.0] - 2025-09-05

### Added

- New `run_stream()` method for streaming results (yields `RunResult` objects).

### Docs

- Refine setup guidance and messaging in `setup.sh`.
- General documentation touch-ups.

### Chore

- Remove legacy `run.sh` wrapper; use examples or direct execution.

## [prior]

- Check commit changelogs for details.
