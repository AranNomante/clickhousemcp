"""ClickHouse support agent that combines PydanticAI with ClickHouse MCP server.

This agent uses a similar pattern to the bank support example but integrates
with ClickHouse via MCP server for database queries.
"""

from dataclasses import dataclass
from typing import Optional
import os

from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStdio

from .env_config import config, logger


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
    query: str,
    host: str,
    port: str = "8443",
    user: str = "demo", 
    password: str = "",
    secure: str = "true",
    model: str = None,
    api_key: str = None
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
    
    if model is None:
        model = config.ai_model
    
    # Determine which model and provider to use
    agent_model = model or config.ai_model
    
    # If API key is provided, set environment variable temporarily
    original_api_key = None
    if api_key:
        original_api_key = os.environ.get('GOOGLE_API_KEY')
        os.environ['GOOGLE_API_KEY'] = api_key
        logger.info(f"Using provided API key for model {model_name}")
    
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
        "CLICKHOUSE_SECURE": secure
    }
    
    # Create MCP server configuration
    # Use the mcp-clickhouse binary from current environment
    server = MCPServerStdio(
        'mcp-clickhouse',  # Binary should be in PATH when venv is activated
        args=[],
        env=env
    )
    
    # Create agent with MCP server
    agent = Agent(
        agent_model,
        deps_type=ClickHouseDependencies,
        output_type=ClickHouseOutput,
        mcp_servers=[server],
        system_prompt=(
            'You are a ClickHouse database analyst. Use the available MCP tools to '
            'query ClickHouse databases and provide insightful analysis. '
            'Always mention the SQL queries you used in your response. '
            'Be precise and include relevant data to support your analysis.'
        ),
    )

    @agent.system_prompt
    async def add_connection_info(ctx: RunContext[ClickHouseDependencies]) -> str:
        """Add ClickHouse connection information to the system prompt."""
        deps = ctx.deps
        connection_info = (
            f"You are connected to ClickHouse at {deps.host}:{deps.port} "
            f"as user '{deps.user}'. "
        )

        connection_info += "Use the available MCP tools to execute queries and analyze data."
        return connection_info

    # Run the agent with MCP servers
    try:
        async with agent.run_mcp_servers():
            result = await agent.run(query, deps=deps)
            return result.output
    except Exception as e:
        logger.error(f"MCP agent execution failed: {e}")
        # Try to provide more specific error information
        if "TaskGroup" in str(e):
            raise Exception("MCP server connection failed. This might be due to network issues or UV environment conflicts.")
        raise
    finally:
        # Restore original API key if it was temporarily set
        if api_key:
            if original_api_key is not None:
                os.environ['GOOGLE_API_KEY'] = original_api_key
            elif 'GOOGLE_API_KEY' in os.environ:
                del os.environ['GOOGLE_API_KEY']


if __name__ == '__main__':
    import asyncio
    
    # Example usage with ClickHouse SQL playground
    async def main():
        # Query the public ClickHouse playground
        result = await run_clickhouse_agent(
            query="What are the top 5 most starred GitHub repositories?",
            host="sql-clickhouse.clickhouse.com",
            port="8443",
            user="demo",
            password="",
            secure="true"
        )
        
        print("Analysis:", result.analysis)
        if result.sql_used:
            print("SQL Used:", result.sql_used)
        print("Confidence:", result.confidence)
        
        # Example with different query
        result2 = await run_clickhouse_agent(
            query="Show me some interesting patterns in the data",
            host="sql-clickhouse.clickhouse.com"
        )
        
        print("\n--- Data Analysis ---")
        print("Analysis:", result2.analysis)
        print("Confidence:", result2.confidence)

    # Check API key using new config
    from .env_config import config, validate_setup
    
    is_valid, issues = validate_setup()
    if not is_valid:
        print("❌ Setup issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print("\n💡 Create a .env file or set environment variables")
    else:
        asyncio.run(main())
