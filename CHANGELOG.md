
# Changelog

## [0.5.0b0] - 2025-08-13

### Major Features

- **Message History & Summarization:**
  - Added robust message history support with token-based summarization and pruning.
  - Prevents runaway token growth and infinite summarization loops.
  - History processor ensures only the pruned list is used for each turn.
  - Fully supports conversational agent workflows.

- **Conversational Agent:**
  - Agent now maintains context across turns using pruned message history.
  - Examples and documentation updated to demonstrate conversational usage.

### Improvements

- All example scripts updated to show correct message history usage and summarization config.
- API key and provider management clarified in both code and documentation.
- Improved error handling and config management for multi-provider scenarios.
- Type safety and code quality maintained throughout.

### Internal

- Refactored agent and processor logic for clarity and maintainability.
- All modules and exports updated for new features.
- Tests and architecture documentation reviewed for consistency.
