"""
Example: Using message history with ClickHouseAgent.run()
"""

import asyncio

from agent.clickhouse_agent import ClickHouseAgent
from agent.config import summarize_config, config

# --- IMPORTANT: Setup summarization config so the example works even if defaults are missing ---
# You must set these before using message history with summarization!
summarize_config.set_ai_model("openai:gpt-3.5-turbo")
summarize_config.set_model_api_key("openai", "your-openai-api-key")  # Replace with your actual API key
summarize_config.set_token_limit(1000)

config.set_ai_model("openai:gpt-4o")
config.set_model_api_key("openai", "your-openai-api-key")  # Replace with your actual API key


async def run_with_message_history() -> None:
    agent = ClickHouseAgent()
    result = await agent.run(
        query="SHOW TABLES FROM analytics",
    )
    print("Analysis:", result.analysis)
    print("SQL Used:", result.sql_used)
    print("Confidence:", result.confidence)
    print("All Messages:", [getattr(m, "content", repr(m)) for m in result.messages])
    print("New Messages:", [getattr(m, "content", repr(m)) for m in result.new_messages])
    print("Last Message:", getattr(result.last_message, "content", repr(result.last_message)))

    result2 = await agent.run(
        query="SHOW COLUMNS FROM analytics.users",
        message_history=result.new_messages,  # Reuse the previous message history
    )
    print("Analysis (with history):", result2.analysis)
    print("SQL Used (with history):", result2.sql_used)
    print("Confidence (with history):", result2.confidence)
    for i, message in enumerate(result2.messages):
        print(f"Message {i} (with history):", getattr(message, "content", repr(message)))


if __name__ == "__main__":
    asyncio.run(run_with_message_history())
