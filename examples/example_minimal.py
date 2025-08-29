"""
Minimal example: Query with all config defaults

NOTE: If your agent or its processors use summarization (e.g., message history summarization),
you must set up summarize_config before running the agent. See example_message_history.py for details.
"""

import asyncio
from agent.clickhouse_agent import ClickHouseAgent
from agent.config import config, summarize_config

# Set up config for model and API key
config.set_log_level("INFO")
# Ensure example-level log statements are printed to the console. The
# package config will install a handler when needed, but calling basicConfig
# here guarantees examples and user-level loggers are wired to the console.
config.set_clickhouse(host="your_host", port="8443", user="readonly_user", password="1234567890Ac!", secure="true")
summarize_config.set_token_limit(10000)
summarize_config.set_ai_model("openai:gpt-5-nano")  # recommended to use a cheaper plan model here
config.set_ai_model("openai:gpt-5-nano")
config.set_model_api_key("openai", "sk-proj-test")


async def run_minimal() -> None:
    agent = ClickHouseAgent()
    result = await agent.run(
        allowed_tables=["example2", "example1"],
        query="can you please give me some insights on the recent data and my console search and ga4 data corelation? for toolswarehouse.in",
    )
    print(result.analysis)


if __name__ == "__main__":
    asyncio.run(run_minimal())
