"""ClickHouse support agent that combines PydanticAI with ClickHouse MCP server.

This agent uses a similar pattern to the bank support example but integrates
with ClickHouse via MCP server for database queries.
"""

import os

from dataclasses import dataclass
from typing import Optional

from pydantic_ai import Agent
from .server_cache import ServerTTLCache


import logging

logger = logging.getLogger(__name__)


@dataclass
class ClickHouseDependencies:
    """Dependencies for ClickHouse connection and MCP server configuration."""

    host: str
    port: str
    user: str
    password: str = ""
    secure: str = "true"


@dataclass
class ClickHouseOutput:
    """Output structure for ClickHouse agent responses."""

    analysis: str
    sql_used: Optional[str] = None
    confidence: int = 5  # Default confidence level (1-10)


class ClickHouseAgent:
    """
    ClickHouse MCP Agent that uses PydanticAI for database queries.

    This agent integrates with ClickHouse via MCP server for efficient querying
    and analysis, leveraging AI models for enhanced insights.
    """

    def __init__(self, max_cache_size: int = 10, cache_ttl: int = 60):
        self.server_cache = ServerTTLCache(maxsize=max_cache_size, ttl=cache_ttl)

    async def run(
        self,
        model_api_key: str,
        model: str,
        query: str,
        host: Optional[str] = None,
        port: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        secure: Optional[str] = None,
    ) -> ClickHouseOutput:
        from .config import config

        # Merge user-provided args with config defaults
        params = dict(
            host=config.clickhouse_host,
            port=config.clickhouse_port,
            user=config.clickhouse_user,
            password=config.clickhouse_password,
            secure=config.clickhouse_secure,
        )
        # Override with any explicit arguments
        if host is not None:
            params["host"] = host
        if port is not None:
            params["port"] = port
        if user is not None:
            params["user"] = user
        if password is not None:
            params["password"] = password
        if secure is not None:
            params["secure"] = secure

        os.environ["GOOGLE_API_KEY"] = model_api_key

        logger.info(f"Running ClickHouse agent query: {query[:50]}...")

        # Create dependencies with connection info
        deps = ClickHouseDependencies(**params)

        # Set up environment for MCP server
        env = {
            "CLICKHOUSE_HOST": params["host"],
            "CLICKHOUSE_PORT": params["port"],
            "CLICKHOUSE_USER": params["user"],
            "CLICKHOUSE_PASSWORD": params["password"],
            "CLICKHOUSE_SECURE": params["secure"],
        }

        # Create MCP server configuration
        server = await self.server_cache.get_server(env)

        # Create agent with MCP server
        agent = Agent(
            model=model,
            deps_type=ClickHouseDependencies,
            output_type=ClickHouseOutput,
            toolsets=[server],
            system_prompt=(
                "You are a ClickHouse database analyst. Use the available MCP tools to "
                "query ClickHouse databases and provide insightful analysis. "
                "Always mention the SQL queries you used in your response. "
                "Be precise and include relevant data to support your analysis."
            ),
            retries=3,
            output_retries=3,
        )

        # Run the agent with MCP servers
        try:
            async with agent:
                result = await agent.run(query, deps=deps)
                return result.output
        except Exception as e:
            logger.error(f"MCP agent execution failed: {e}")
            if "TaskGroup" in str(e):
                raise Exception(
                    "MCP server connection failed. This might be due to network issues or UV environment conflicts."
                )
            raise
        finally:
            os.environ.pop("GOOGLE_API_KEY", None)
