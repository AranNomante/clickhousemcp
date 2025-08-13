"""
Example: Using message history with ClickHouseAgent.run()
"""

import asyncio
from agent.clickhouse_agent import ClickHouseAgent
from agent.config import summarize_config, config

# --- IMPORTANT: Setup summarization config so the example works even if defaults are missing ---
# You must set these before using message history with summarization!
summarize_config.set_ai_model("openai:gpt-3.5-turbo")
summarize_config.set_model_api_key("openai", "your-api-key")
summarize_config.set_token_limit(1000)

config.set_ai_model("openai:gpt-4o")
config.set_model_api_key("openai", "your-api-key")


async def run_with_message_history() -> None:
    agent = ClickHouseAgent()
    result = await agent.run(
        query="SHOW TABLES FROM twitter",
    )

    result2 = await agent.run(
        query="explain the contents and give some insights be thorough",
        message_history=result.messages,  # Reuse the previous message history
    )

    print("Analysis (with history):", result2.analysis)
    print("SQL Used (with history):", result2.sql_used)
    print("Confidence (with history):", result2.confidence)
    print("Usage (with history):", result2.usage)


if __name__ == "__main__":
    asyncio.run(run_with_message_history())
