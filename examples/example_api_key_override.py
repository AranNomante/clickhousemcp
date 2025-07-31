"""
Example: Explicit API key override at runtime
"""

import asyncio
from agent.clickhouse_agent import ClickHouseAgent, ModelProvider
from agent.config import config

# Set up config for model and logging
config.set_ai_model("groq:llama3-8b")  # Example: use a GROQ-compatible model
config.set_log_level("INFO")


async def run_api_key_override() -> None:
    agent = ClickHouseAgent()
    print("\n--- [4] Query with explicit API key override ---")
    result = await agent.run(
        model=config.ai_model,  # Should match the provider
        query="SHOW DATABASES",
        provider=ModelProvider.GROQ,
        model_api_key="your-groq-api-key",
        # No host/port/user/password/secure provided
    )
    print("Analysis:", result.analysis)
    print("SQL Used:", result.sql_used)
    print("Confidence:", result.confidence)


if __name__ == "__main__":
    asyncio.run(run_api_key_override())
