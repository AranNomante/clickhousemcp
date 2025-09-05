"""
ClickHouse MCP Agent Package

Provides a PydanticAI agent for querying ClickHouse databases via MCP server.
"""

from .clickhouse_agent import ClickHouseAgent, ClickHouseDependencies, ClickHouseOutput
from .config import ClickHouseConfig, ClickHouseConnections, EnvConfig, config
from .history_processor import summarize_old_messages, history_processor
from .default_instruction import DefaultInstructions

__all__ = [
    "ClickHouseAgent",
    "ClickHouseDependencies",
    "ClickHouseOutput",
    "ClickHouseConfig",
    "ClickHouseConnections",
    "EnvConfig",
    "config",
    "summarize_old_messages",
    "history_processor",
    "DefaultInstructions",
]
