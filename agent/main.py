"""Enhanced ClickHouse agent with configuration management."""

import asyncio

from agent.clickhouse_agent import run_clickhouse_agent, ClickHouseOutput
from agent.config import ClickHouseConnections, ClickHouseConfig, get_connection_string
from agent.env_config import config as env_config


async def query_clickhouse(
    query: str, connection: str = "playground", model: str = "gemini-2.0-flash", api_key: str = "your_api_key_here"
) -> ClickHouseOutput:
    """
    Query ClickHouse using a predefined connection configuration.

    Args:
        query: The question or analysis request
        connection: Connection name ('playground', 'local', 'env') or ClickHouseConfig
        model: AI model to use
        api_key: AI API key (if not provided, uses environment variables)

    Returns:
        ClickHouseOutput with analysis results
    """

    # Use default model if not specified
    if model is None:
        model = env_config.ai_model

    # Get configuration
    if isinstance(connection, str):
        config = ClickHouseConnections.get_config(connection)
        if not config:
            raise ValueError(f"Unknown connection: {connection}")
    elif isinstance(connection, ClickHouseConfig):
        config = connection
    else:
        raise ValueError("connection must be a string or ClickHouseConfig")

    print(f"🔌 Connecting to: {get_connection_string(config)}")

    return await run_clickhouse_agent(
        query=query,
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        secure=config.secure,
        model=model,
        model_api_key=api_key,
    )


async def interactive_demo() -> None:
    """Interactive demo showing ClickHouse agent capabilities."""
    print("🎯 ClickHouse AI Agent Demo")
    print("=" * 40)

    # Check API key first
    from agent.env_config import config as env_config

    if not env_config.has_api_key:
        print("❌ No API key found! Please set GOOGLE_API_KEY in your .env file")
        return

    print(f"✅ Using AI model: {env_config.ai_model}")
    print()

    # Show available connections
    print("📡 Available ClickHouse connections:")
    for name, config in ClickHouseConnections.list_configs().items():
        print(f"  • {name}: {get_connection_string(config)}")
    print()

    # Show MCP tools info
    print("� Available MCP Tools:")
    print("  • run_select_query - Execute SELECT queries")
    print("  • list_databases - List all available databases")
    print("  • list_tables - List tables in a specific database")
    print("  • describe_table - Get table schema and structure")
    print()

    # Show example usage
    print("💡 Example usage:")
    print("  from agent import query_clickhouse")
    print("  result = await query_clickhouse('SHOW DATABASES', 'playground')")
    print()

    print("🚀 Ready to analyze ClickHouse data!")
    print("   Run queries programmatically or extend this demo for interactive use.")


if __name__ == "__main__":
    asyncio.run(interactive_demo())


def cli_main() -> None:
    """Entry point for CLI command."""
    import sys

    # Handle --help flag without running the demo
    if len(sys.argv) > 1 and sys.argv[1] in ["--skip", "-s"]:
        print("Skipping interactive demo. You can run queries directly using the query_clickhouse function.")
        return

    # Run the interactive demo
    asyncio.run(interactive_demo())
