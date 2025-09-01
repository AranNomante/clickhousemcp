
# Changelog

## [0.7.0] - 2025-08-29

### Fixes

- Make model API key handling safe: do not set env vars when key is `None` and avoid overwriting existing vars.
- Lazily initialize MCP server and `Agent` to allow `ClickHouseAgent()` instantiation without provider credentials (unblocks tests and minimal setups).

### Internal

- Preserve per-call `allowed_tables` behavior in deps construction; no implicit merging.

### Docs

- Update version badge and architecture notes to 0.7.0.

## [prior]

### Info

- Check commit changelogs for details.
