"""
Example usage of ClickHouse MCP Agent library.

This script demonstrates how to configure and use the agent for querying ClickHouse databases.
"""

import asyncio
from agent.clickhouse_agent import ClickHouseAgent
from agent.config import ClickHouseConnections, get_connection_string, config

# Set up config for model and logging (optional, applies globally)
config.set_ai_model("gemini-2.0-flash")
config.set_log_level("INFO")

print("\nClickHouse MCP Agent Example: Explicit Connection Parameters")
print("==============================================================")


async def run_explicit() -> None:
    # 1. Explicit connection: uses predefined config, does NOT affect global config
    ch_config = ClickHouseConnections.get_config("playground")
    if ch_config is None:
        print("Error: Could not find connection config for 'playground'.")
        return
    print(f"Prepared connection string: {get_connection_string(ch_config)}")

    agent = ClickHouseAgent()
    print("\n--- [1] Query with explicit connection parameters (predefined config) ---")
    result = await agent.run(
        model_api_key="your_api_key_here",  # Set your API key here
        model=config.ai_model,
        query="SHOW DATABASES",
        host=ch_config.host,
        port=ch_config.port,
        user=ch_config.user,
        password=ch_config.password,
        secure=ch_config.secure,
    )
    print("Analysis:", result.analysis)
    print("SQL Used:", result.sql_used)
    print("Confidence:", result.confidence)


asyncio.run(run_explicit())

print("\nClickHouse MCP Agent Example: Config Defaults (Preset)")
print("========================================================")

# 2. Config preset: uses current global config
default_host = "sql-clickhouse.clickhouse.com"
default_user = "demo"
config.set_clickhouse(host=default_host, user=default_user)
print(f"Current config defaults: host={config.clickhouse_host}, user={config.clickhouse_user}")


async def run_config_default() -> None:
    agent = ClickHouseAgent()
    print("\n--- [2] Query using config defaults (no connection parameters) ---")
    result = await agent.run(
        model_api_key="your_api_key_here",
        model=config.ai_model,
        query="SHOW DATABASES",
        # No host/port/user/password/secure provided
    )
    print("Analysis:", result.analysis)
    print("SQL Used:", result.sql_used)
    print("Confidence:", result.confidence)


asyncio.run(run_config_default())


print("\nClickHouse MCP Agent Example: User Override of Config Defaults")
print("==============================================================")

# 3. User override: change config at runtime, subsequent queries use new defaults
# Uncomment and set a valid host/user to use this example:
# config.set_clickhouse(host="custom-host.example.com", user="custom_user")
# print(f"Config changed by user: host={config.clickhouse_host}, user={config.clickhouse_user}")


async def run_user_override() -> None:
    agent = ClickHouseAgent()
    print("\n--- [3] Query after user changes config defaults ---")
    result = await agent.run(
        model_api_key="your_api_key_here",
        model=config.ai_model,
        query="SHOW DATABASES",
        # No host/port/user/password/secure provided
    )
    print("Analysis:", result.analysis)
    print("SQL Used:", result.sql_used)
    print("Confidence:", result.confidence)


asyncio.run(run_user_override())
