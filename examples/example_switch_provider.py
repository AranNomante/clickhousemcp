"""
Example: Switch provider/model at runtime
"""

import asyncio
from agent.clickhouse_agent import ClickHouseAgent
from agent.config import config

# Set API keys for both providers
config.set_model_api_key("openai", "your-openai-api-key")
config.set_model_api_key("anthropic", "your-anthropic-api-key")


async def run_switch() -> None:
    agent = ClickHouseAgent()
    # Query with OpenAI GPT-4o
    result_openai = await agent.run(model="openai:gpt-4o", query="SHOW TABLES")
    print("OpenAI result:", result_openai.analysis)
    # Switch to Anthropic Claude 3 Sonnet
    result_claude = await agent.run(model="anthropic:claude-3-sonnet-20240229", query="SHOW CLUSTERS")
    print("Anthropic result:", result_claude.analysis)


if __name__ == "__main__":
    asyncio.run(run_switch())
