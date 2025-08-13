"""ClickHouse support agent that combines PydanticAI with ClickHouse MCP server.

This agent uses a similar pattern to the bank support example but integrates
with ClickHouse via MCP server for database queries.
"""

import os

from dataclasses import dataclass
from typing import Optional
from enum import Enum

from pydantic_ai import Agent
from .server_cache import ServerTTLCache
from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import Usage

import logging


# Enum for supported model providers
class ModelProvider(Enum):
    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    MISTRAL = "mistral"
    CO = "co"


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

    """Analysis of the query result."""
    analysis: str

    """Confidence level of the analysis (1-10)."""
    confidence: int

    """SQL query used to generate the result."""
    sql_used: Optional[str] = None


@dataclass
class RunResult:
    """Result structure for agent run method."""

    """Messages exchanged during the query."""
    messages: list[ModelMessage]

    """New messages added during the query execution."""
    new_messages: list[ModelMessage]

    usage: Usage

    """Analysis of the query result."""
    analysis: str

    """Confidence level of the analysis (1-10)."""
    confidence: int

    """SQL query used to generate the result."""
    sql_used: Optional[str] = None

    """Last message in the conversation, useful for context."""
    last_message: Optional[ModelMessage] = None


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
        query: str,
        model: Optional[str] = None,
        model_api_key: Optional[str] = None,
        provider: Optional[ModelProvider] = None,
        host: Optional[str] = None,
        port: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        secure: Optional[str] = None,
        message_history: Optional[list[ModelMessage]] = None,
    ) -> RunResult:
        from .config import config

        # Determine provider: use argument if given, else config default
        selected_provider = provider.value if provider else config.model_provider

        model = model or config.ai_model

        # Use provided key if given, else get from config
        if model_api_key is None:
            api_key_attr = f"{selected_provider.upper()}_API_KEY"
            model_api_key = getattr(config.model_api, api_key_attr, None)
            if not model_api_key:
                raise ValueError(f"API key for provider '{selected_provider}' is not set.")

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

        # Set API key in environment for selected provider
        os.environ[api_key_attr] = model_api_key

        logger.info(f"Running ClickHouse agent query: {query[:50]}... (provider: {selected_provider})")

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

        from .history_processor import history_processor

        # Create agent with MCP server
        agent = Agent(
            model=model,
            deps_type=ClickHouseDependencies,
            output_type=ClickHouseOutput,
            toolsets=[server],
            instructions="You are a ClickHouse database analyst. Use the available MCP tools to query ClickHouse databases and provide insightful analysis. Always mention the SQL queries you used in your response. Be precise and include relevant data to support your analysis.",
            retries=3,
            output_retries=3,
        )

        total_tokens = 0

        for m in message_history if message_history else []:
            if hasattr(m, "usage"):
                total_tokens += m.usage.total_tokens

        message_history = await history_processor(total_tokens, message_history)

        # Run the agent with MCP servers
        try:
            async with agent:
                result = await agent.run(query, deps=deps, message_history=message_history)

                all_messages = result.all_messages()
                new_messages = result.new_messages()
                usage = result.usage()
                output = result.output

                return RunResult(
                    messages=all_messages,
                    last_message=all_messages[-1] if all_messages else None,
                    new_messages=new_messages,
                    usage=usage,
                    analysis=output.analysis,
                    sql_used=output.sql_used,
                    confidence=output.confidence,
                )
        except Exception as e:
            logger.error(f"MCP agent execution failed: {e}")
            if "TaskGroup" in str(e):
                raise Exception(
                    "MCP server connection failed. This might be due to network issues or UV environment conflicts."
                )
            raise
        finally:
            os.environ.pop(api_key_attr, None)
