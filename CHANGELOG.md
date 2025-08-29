
# Changelog

## [0.6.0b0] - 2025-08-29

### Internal

- Refactor to single MCP server and single `Agent` instance; remove `ServerTTLCache`.
- Add allow-list injection in `process_tool_call` so `allowed_dbs`/`allowed_tables` flow into MCP tool calls.
- Update history processor to gate summarization by provider via `summarize_config`.

### Documentation

- Update README and ARCHITECTURE to reflect single MCP server, single-agent design.
- Clarify access restriction via per-call allow-lists (`allowed_dbs`, `allowed_tables`) instead of multi-key/multi-agent approaches.
- Update version badge and version references.
