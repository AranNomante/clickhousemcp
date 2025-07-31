"""
Example: Explicit connection parameters and provider override
"""

import asyncio
from agent.clickhouse_agent import ClickHouseAgent, ModelProvider
from agent.config import ClickHouseConnections, get_connection_string, config

# Set up config for model, logging, and API keys (applies globally)
config.set_ai_model("openai:gpt-4o")  # Example: use an OpenAI-compatible model
config.set_log_level("INFO")
config.set_model_api_key("openai", "your-openai-api-key")


async def run_explicit() -> None:
    ch_config = ClickHouseConnections.get_config("playground")
    if ch_config is None:
        print("Error: Could not find connection config for 'playground'.")
        return
    print(f"Prepared connection string: {get_connection_string(ch_config)}")

    agent = ClickHouseAgent()
    print("\n--- [1] Query with explicit connection parameters and provider override ---")
    result = await agent.run(
        model=config.ai_model,
        query="SHOW DATABASES",
        provider=ModelProvider.OPENAI,
        host=ch_config.host,
        port=ch_config.port,
        user=ch_config.user,
        password=ch_config.password,
        secure=ch_config.secure,
    )
    print("Analysis:", result.analysis)
    print("SQL Used:", result.sql_used)
    print("Confidence:", result.confidence)


if __name__ == "__main__":
    asyncio.run(run_explicit())
