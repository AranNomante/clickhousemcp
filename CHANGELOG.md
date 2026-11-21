
# Changelog

## [0.13.0] - 2026-11-21

### Fixed

- **History summarization wiped the conversation.** `summarize_old_messages` returned the summarizer's first new message, an empty `ModelRequest`, and dropped the summary. It now returns one user message with the summary text, which is valid history for every provider.
- **Summarization triggered far too early.** Token usage was summed over every response, but each response's input already includes the earlier messages. The latest response's usage is now used as the context size.
- **Summarizer API key was ignored.** `summarize_config.set_model_api_key()` is now applied, and summarization no longer requires the same provider as the main agent. It's skipped with a warning only when no key is available.
- **`ClickHouseConnections.LOCAL` used port 9000** (native protocol). `mcp-clickhouse` speaks HTTP, so it's now 8123.
- **Model and provider could disagree.** `set_ai_model("openai:...")` now also sets `model_provider` from the prefix, so the right API key is used.
- **API keys set after construction, or over an existing env var, were ignored.** Keys are now exported when the agent is first built, and an explicit `set_model_api_key` overrides the environment.
- Cached `RunResult`s are returned as copies, so mutating a result no longer corrupts the cache.
- `run_batch` summarizes shared `message_history` once instead of once per query.
- MCP connection errors are detected by exception type (exception groups), not only by message text.
- `setup.sh` no longer tells you to configure a `.env` file the library never reads.

### Added

- `config.use_connection("local" | "playground" | ClickHouseConfig)` applies a connection preset.
- `config.set_clickhouse()` accepts `int` ports and `bool` flags, plus `database`, `role`, `verify`, `connect_timeout`, `send_receive_timeout` and `query_timeout`, which are passed to `mcp-clickhouse`.
- `run_batch(..., return_exceptions=True)` keeps successful results when some queries fail.
- `ClickHouseAgent.last_sql_used`: SQL from the most recent `run()` / `run_stream()`.

### Changed

- **Default `summarize_config.token_limit` raised from 1,000 to 50,000.** Tool definitions and instructions alone are ~600 tokens per request, so with summarization now working, the old default would have compressed the history to a 50-word summary on nearly every follow-up and added an extra LLM call per turn. Set it explicitly to keep the old behavior.
- Summarization now runs when the summarizer's provider differs from the main agent's, as long as a key is available (from `summarize_config.set_model_api_key()` or the env var). Previously it was always skipped.
- A key passed to `set_model_api_key()` now overwrites an existing env var of the same name.
- The MCP server is launched as `sys.executable -m mcp_clickhouse.main`, so it works when the venv's scripts directory isn't on `PATH`.

### Tests

- `tests/test_openai_wire.py` + `tests/fake_openai_server.py`: the agent talks over real HTTP to a fake OpenAI-compatible server, through pydantic-ai's real OpenAI provider and the real `mcp-clickhouse` server. The fake server rejects requests the real API would reject (conversation starting with the assistant, unanswered or orphaned tool calls), so these tests check provider selection, API-key export and that summarized history is accepted. With the old summarizer bug, the follow-up request is rejected with a 400. No API key or model needed; runs in the normal test job.
- Live tests for `role=` (a user with no direct grants and two roles; the active role decides what's readable) and `query_timeout=`. `seed_live.py` creates the user and roles.
- `scripted_model` also records tool errors (retry prompts), so tests can assert on them.

### CI

- Pinned the ClickHouse image to `clickhouse/clickhouse-server:26.8.42.13` (LTS) in CI and `docker-compose.yml` instead of `latest`, so live tests are reproducible.
- CI checks formatting (`ruff format --check .`); reformatted the repo with `ruff format .`.

---

## [0.12.1] - 2026-10-29

### Fixed

- **Allow-list filtering bypassed with real server responses.** `mcp-clickhouse` tools return JSON *strings*, which pydantic-ai passes to `process_tool_call` unparsed. The filters only handled Python lists/dicts, so `list_databases` returned every database even with `allowed_databases` set, and `list_tables` with `allowed_tables` patterns returned no tables at all. Results are now decoded before filtering, and an undecodable listing returns empty when an allow-list is active (fail closed).
- **Test suite crashed on fresh installs.** Newer pytest-asyncio emits a deprecation warning that `filterwarnings = error` turned into an INTERNALERROR. Set `asyncio_default_fixture_loop_scope = "function"`.
- **Grok/Groq provider confusion.** The `grok` extra did not exist, and the README's `grok:llama-3.3-70b-versatile` example pointed a Groq model at xAI's API. Added the `groq` and `xai` extras, `GROQ_API_KEY` / `XAI_API_KEY` support, and corrected examples (`groq:llama-3.3-70b-versatile`, `xai:grok-4`). `GROK_API_KEY` is kept for the legacy `grok:` prefix.

### Changed

- Docs: allow-lists are documented as discovery scoping, not access control. `run_query` SQL is not filtered by them; use ClickHouse grants to restrict reads (README → Security).
- README PyPI badge now shows the live published version.

### Tests / CI

- `tests/test_wire_format.py`: unit tests using the JSON-string wire format.
- `tests/test_contract.py`: runs the real `mcp-clickhouse` server over stdio (ClickHouse client faked) with a scripted model; no API key needed.
- `tests/test_clickhouse_live.py` + CI job `live-clickhouse`: real ClickHouse service container, seeded from `docker/init.sql`.
- CI lints the whole repo (`ruff check .`); fixed existing lint errors in `examples/` and `tests/`.

---

## [0.12.0] - 2026-06-07

### Changed

- API locked — no breaking changes without a major version from here.
- MCPServerStdio → MCPToolset migration intentionally deferred: blocked on `mcp-clickhouse` upgrading its fastmcp pin to 3.x.
- Updated to `mcp-clickhouse` 0.4.0.
- Default model updated from `gemini-2.5-flash` to `google:gemini-3.1-flash-lite` in both `EnvConfig` and `SummarizeAgentEnv`.
- Dependencies exact-pinned: `pydantic-ai-slim==1.96.1`, `mcp-clickhouse==0.4.0`.

### Fixed

- **`list_databases` enforcement**: `mcp-clickhouse` 0.4.0 added a `list_databases` tool that was not intercepted by `process_tool_call`, letting the agent see all databases even when `allowed_databases` was set. Now filtered: returns only databases in the allow-list, or empty when `allowed_databases=[]`.

### CI

- `mypy agent/` added to CI matrix.
- `py.typed` marker presence verified in CI on every build.

---

## [0.11.2] - 2026-06-07

### Fixed

- **Cache write bug**: `run()` was checking `message_history is None` to decide whether to store a result in the cache, but by that point `message_history` had already been overwritten by `_use_history_processor()` which always returns a list. Results were looked up correctly on cache hit but never written on cache miss. Fixed by capturing `is_stateless = message_history is None` before calling the processor.

---

## [0.11.0] - 2026-06-07

### Added

- `ClickHouseAgent.run_batch(queries, *, allowed_tables, allowed_databases, message_history)` — runs a list of queries concurrently using `asyncio.create_task`, returning results in input order. Recommended inside `async with ClickHouseAgent()` to avoid per-query MCP server restarts.
- `ClickHouseAgent.reset()` — tears down the MCP subprocess and agent state so the next `run()` re-initializes from scratch. Intended for one-shot mode; in persistent-server mode prefer exiting the `async with` block.
- Query result cache: `ClickHouseAgent(enable_cache=True)` caches `RunResult` objects keyed by `(query, frozenset(allowed_tables), frozenset(allowed_databases))`. Only stateless calls (no `message_history`) are cached.
- `structlog` optional dependency: `pip install "clickhouse-mcp-agent[logging]"`. If `structlog` is installed it is used as the library logger automatically; standard `logging` is the fallback.

### Fixed

- **Bug #1 (concurrent SQL mixing)**: `_sql_used` is now tracked via a `contextvars.ContextVar` set at the start of each `run()` / `run_stream()` call. Each asyncio task created by `run_batch()` has its own SQL list — no mixing between concurrent queries. The `self._sql_used` instance attribute is kept in sync after each call for backward compatibility with tests that access it directly.

### Changed

- Default model updated from `gemini-2.0-flash` to `gemini-2.5-flash` in both `EnvConfig` and `SummarizeAgentEnv`.
- `process_tool_call` logging now uses `%s` format (compatible with both `structlog` and standard `logging`).

### Audit / Notes

- **pydantic-ai 1.96.1 API audit**: `toolsets=` parameter is still correct. `MCPToolset` is not available in this version — `MCPServerStdio` migration remains blocked on `mcp-clickhouse`'s fastmcp pin.
- **Bug #2 (run_stream double-start)**: Confirmed non-issue. `MCPServerStdio.__aenter__` uses reference counting — re-entering while already in context is safe and idempotent.

---

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
- `README.md`: removed `result.sql_used` from quickstart example and output section; added Local Development (Docker) section; added provider-switching examples for Anthropic, Google, and Grok; updated roadmap with concrete planned features.
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
