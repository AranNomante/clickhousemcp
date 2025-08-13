"""
Example: Error handling for missing API key

NOTE: If your agent or its processors use summarization (e.g., message history summarization),
you must set up summarize_config before running the agent. See example_message_history.py for details.
"""

import asyncio
from agent.clickhouse_agent import ClickHouseAgent
from agent.config import config

# Intentionally do NOT set API key for provider
config.set_ai_model("openai:gpt-4o")


async def run_error() -> None:
    agent = ClickHouseAgent()
    try:
        result = await agent.run(model=config.ai_model, query="SHOW SETTINGS")
        print("Result:", result.analysis)
    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    asyncio.run(run_error())
