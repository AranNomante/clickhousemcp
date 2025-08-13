"""
Example: Using config defaults and default provider

NOTE: If your agent or its processors use summarization (e.g., message history summarization),
you must set up summarize_config before running the agent. See example_message_history.py for details.
"""

import asyncio
from agent.clickhouse_agent import ClickHouseAgent
from agent.config import config

# Set up config for model, logging, and API keys (applies globally)
config.set_ai_model("gemini-2.0-flash")
config.set_log_level("INFO")
config.set_model_api_key("google", "your-google-api-key")

# Set config defaults
default_host = "sql-clickhouse.clickhouse.com"
default_user = "demo"
config.set_clickhouse(host=default_host, user=default_user)
print(f"Current config defaults: host={config.clickhouse_host}, user={config.clickhouse_user}")


async def run_config_default() -> None:
    agent = ClickHouseAgent()
    print("\n--- [2] Query using config defaults and default provider ---")
    result = await agent.run(
        model=config.ai_model,
        query="SHOW DATABASES",
        # No provider or model_api_key: uses config default
    )
    print("Analysis:", result.analysis)
    print("SQL Used:", result.sql_used)
    print("Confidence:", result.confidence)


if __name__ == "__main__":
    asyncio.run(run_config_default())
