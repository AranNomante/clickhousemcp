"""ClickHouse MCP Agent Package.

This package provides a PydanticAI agent that can query ClickHouse databases
using the Model Context Protocol (MCP) server.
"""

from .clickhouse_agent import run_clickhouse_agent, ClickHouseDependencies, ClickHouseOutput
from .config import ClickHouseConfig, ClickHouseConnections
from .main import query_clickhouse
from .env_config import EnvConfig, config

__all__ = [
    'run_clickhouse_agent',
    'query_clickhouse', 
    'ClickHouseDependencies',
    'ClickHouseOutput',
    'ClickHouseConfig',
    'ClickHouseConnections',
    'EnvConfig',
    'config'
] 