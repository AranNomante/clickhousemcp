"""Custom exception hierarchy for clickhouse-mcp-agent."""


class ClickHouseMCPError(Exception):
    """Base exception for all clickhouse-mcp-agent errors."""


class MCPConnectionError(ClickHouseMCPError):
    """Raised when the MCP server subprocess cannot be started or the connection is lost."""


class AgentExecutionError(ClickHouseMCPError):
    """Raised when the PydanticAI agent fails during a run."""


class HistoryProcessorError(ClickHouseMCPError):
    """Raised when the history summarization agent fails."""
