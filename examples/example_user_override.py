"""
Example: User override of config defaults and provider

NOTE: If your agent or its processors use summarization (e.g., message history summarization),
you must set up summarize_config before running the agent. See example_message_history.py for details.
"""

import asyncio
from agent.clickhouse_agent import ClickHouseAgent, ModelProvider
from agent.config import config

# Set up config for model, logging, and API keys (applies globally)
config.set_ai_model("anthropic:claude-3-sonnet")  # Example: use an Anthropic-compatible model
config.set_log_level("INFO")
config.set_model_api_key("anthropic", "your-anthropic-api-key")

# Uncomment and set a valid host/user to use this example:
# config.set_clickhouse(host="custom-host.example.com", user="custom_user")
# print(f"Config changed by user: host={config.clickhouse_host}, user={config.clickhouse_user}")


async def run_user_override() -> None:
    agent = ClickHouseAgent()
    print("\n--- [3] Query after user changes config defaults and provider ---")
    result = await agent.run(
        model=config.ai_model,
        query="SHOW DATABASES",
        provider=ModelProvider.ANTHROPIC,
        # model_api_key can be omitted to use config, or set explicitly:
        # model_api_key="your-anthropic-api-key",
        # No host/port/user/password/secure provided
    )
    print("Analysis:", result.analysis)
    print("SQL Used:", result.sql_used)
    print("Confidence:", result.confidence)


if __name__ == "__main__":
    asyncio.run(run_user_override())
