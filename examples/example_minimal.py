"""
Minimal example: Query with all config defaults

NOTE: If your agent or its processors use summarization (e.g., message history summarization),
you must set up summarize_config before running the agent. See example_message_history.py for details.
"""

import asyncio
from agent.clickhouse_agent import ClickHouseAgent
from agent.config import config

# Set up config for model and API key
config.set_ai_model("openai:gpt-4o")
config.set_model_api_key("openai", "your-openai-api-key")


async def run_minimal() -> None:
    agent = ClickHouseAgent()
    result = await agent.run(model=config.ai_model, query="SHOW DATABASES")
    print("Analysis:", result.analysis)
    print("SQL Used:", result.sql_used)
    print("Confidence:", result.confidence)


if __name__ == "__main__":
    asyncio.run(run_minimal())
