"""
Minimal example: Query with all config defaults

NOTE: If your agent or its processors use summarization (e.g., message history summarization),
you must set up summarize_config before running the agent. See example_message_history.py for details.
"""

import asyncio
from agent.clickhouse_agent import ClickHouseAgent
from agent.config import config

# Set up config for model and API key
config.set_log_level("DEBUG")
# Ensure example-level log statements are printed to the console. The
# package config will install a handler when needed, but calling basicConfig
# here guarantees examples and user-level loggers are wired to the console.

config.set_ai_model("gemini-2.0-flash")
config.set_model_api_key("google", "your_api_key_here")


async def run_minimal() -> None:
    agent = ClickHouseAgent()
    result0 = await agent.run(allowed_tables=["top_repos_mv"], allowed_dbs=["github"], query="SHOW_TABLES")
    print("Analysis:", result0.analysis)
    result = await agent.run(allowed_tables=["top_repos_mv"], allowed_dbs=["github"])
    print("Analysis:", result.analysis)
    print("SQL Used:", result.sql_used)
    print("Confidence:", result.confidence)


if __name__ == "__main__":
    asyncio.run(run_minimal())
