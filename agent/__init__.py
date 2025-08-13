"""
ClickHouse MCP Agent Package

Provides a PydanticAI agent for querying ClickHouse databases via MCP server.
"""

from .clickhouse_agent import ClickHouseAgent, ClickHouseDependencies, ClickHouseOutput
from .server_cache import ServerTTLCache
from .config import ClickHouseConfig, ClickHouseConnections, EnvConfig, config
from .history_processor import summarize_old_messages, history_processor

__all__ = [
    "ClickHouseAgent",
    "ClickHouseDependencies",
    "ClickHouseOutput",
    "ServerTTLCache",
    "ClickHouseConfig",
    "ClickHouseConnections",
    "EnvConfig",
    "config",
    "summarize_old_messages",
    "history_processor",
]
