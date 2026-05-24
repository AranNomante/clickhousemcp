"""
ClickHouse MCP Agent Package

Provides a PydanticAI agent for querying ClickHouse databases via MCP server.
"""

from .clickhouse_agent import ClickHouseAgent, ClickHouseDependencies, ClickHouseOutput
from .config import ClickHouseConfig, ClickHouseConnections, EnvConfig, config, summarize_config
from .default_instruction import DefaultInstructions
from .history_processor import history_processor, summarize_old_messages

__all__ = [
    "ClickHouseAgent",
    "ClickHouseDependencies",
    "ClickHouseOutput",
    "ClickHouseConfig",
    "ClickHouseConnections",
    "EnvConfig",
    "config",
    "summarize_config",
    "summarize_old_messages",
    "history_processor",
    "DefaultInstructions",
]
