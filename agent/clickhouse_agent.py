"""ClickHouse support agent that combines PydanticAI with ClickHouse MCP server.

This agent uses a similar pattern to the bank support example but integrates
with ClickHouse via MCP server for database queries.
"""

import os

from dataclasses import dataclass
from typing import Optional

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

from .env_config import logger


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


async def run_clickhouse_agent(
    model_api_key: str,
    model: str,
    query: str,
    host: str,
    port: str = "8443",
    user: str = "demo",
    password: str = "",
    secure: str = "true",
) -> ClickHouseOutput:
    """
    Run a query against ClickHouse using the MCP-enabled agent.

    Args:
        query: The question or analysis request
        host: ClickHouse host
        port: ClickHouse port
        user: ClickHouse username
        password: ClickHouse password
        secure: Whether to use secure connection
        model: AI model to use
        api_key: AI API key (if not provided, uses environment variables)

    Returns:
        ClickHouseOutput with analysis results
    """

    os.environ["GOOGLE_API_KEY"] = model_api_key

    logger.info(f"Running ClickHouse agent query: {query[:50]}...")

    # Create dependencies with connection info
    deps = ClickHouseDependencies(
        host=host,
        port=port,
        user=user,
        password=password,
        secure=secure,
    )

    # Set up environment for MCP server
    env = {
        "CLICKHOUSE_HOST": host,
        "CLICKHOUSE_PORT": port,
        "CLICKHOUSE_USER": user,
        "CLICKHOUSE_PASSWORD": password,
        "CLICKHOUSE_SECURE": secure,
    }

    # Create MCP server configuration
    # Use the mcp-clickhouse binary from current environment
    server = MCPServerStdio("mcp-clickhouse", args=[], env=env)  # Binary should be in PATH when venv is activated
    
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
        # Try to provide more specific error information
        if "TaskGroup" in str(e):
            raise Exception(
                "MCP server connection failed. This might be due to network issues or UV environment conflicts."
            )
        raise
    finally:
        del os.environ["GOOGLE_API_KEY"]


if __name__ == "__main__":
    import asyncio

    # Example usage with ClickHouse SQL playground
    async def main() -> None:
        # Query the public ClickHouse playground
        result = await run_clickhouse_agent(
            model_api_key=os.environ.get("GOOGLE_API_KEY", "your_api_key_here"),
            model="gemini-2.0-flash",
            query="What can I do with ClickHouse?",
            host="sql-clickhouse.clickhouse.com",
            port="8443",
            user="demo",
            password="",
            secure="true",
        )

        print("Analysis:", result.analysis)
        print("SQL Used: N/A")
        print("Confidence:", result.confidence)

        # Example with different query
        result2 = await run_clickhouse_agent(
            model_api_key=os.environ.get("GOOGLE_API_KEY", "your_api_key_here"),
            model="gemini-2.0-flash",
            query="Show me some interesting patterns in the data",
            host="sql-clickhouse.clickhouse.com",
        )

        print("\n--- Data Analysis ---")
        print("Analysis:", result2.analysis)
        print("Confidence:", result2.confidence)
        print("SQL Used:", result2.sql_used if result2.sql_used else "N/A")

    asyncio.run(main())
