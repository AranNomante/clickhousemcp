
# Changelog

## [0.7.0] - 2025-08-29

### Fixes

- Make model API key handling safe: do not set env vars when key is `None` and avoid overwriting existing vars.
- Lazily initialize MCP server and `Agent` to allow `ClickHouseAgent()` instantiation without provider credentials (unblocks tests and minimal setups).

### Internal

- Preserve per-call `allowed_tables` behavior in deps construction; no implicit merging.

### Docs

- Update version badge and architecture notes to 0.7.0.

## [0.6.0b0] - 2025-08-29

### Internal

- Refactor to single MCP server and single `Agent` instance; remove `ServerTTLCache`.
- Add allow-list injection in `process_tool_call` so `allowed_dbs`/`allowed_tables` flow into MCP tool calls.
- Update history processor to gate summarization by provider via `summarize_config`.

### Documentation

- Update README and ARCHITECTURE to reflect single MCP server, single-agent design.
- Clarify access restriction via per-call allow-lists (`allowed_dbs`, `allowed_tables`) instead of multi-key/multi-agent approaches.
- Update version badge and version references.
