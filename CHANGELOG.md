
# Changelog

## [Unreleased — targeting 0.10.0]

### To fix
- Rewrite `default_instruction.py` system prompt
- Fix dead field docstrings in `ClickHouseOutput` / `RunResult`
- Rename camelCase internal methods to snake_case
- Remove dead `ModelProvider` enum
- Fix `run_stream()` return type annotation
- Remove logging handler installation from library code
- Document `allowed_tables=[]` behaviour
- `secure: str` → `bool` in `ClickHouseDependencies`

### To add
- Custom exception hierarchy
- `sql_used` extraction
- `allowed_databases` parameter
- `async with ClickHouseAgent()` context manager
- Persistent MCP server across calls
- Integration tests

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

### Info

- Check commit changelogs for details.
