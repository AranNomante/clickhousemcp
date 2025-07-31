"""
Example: Multiple queries in a loop with different models/providers
"""

import asyncio
from agent.clickhouse_agent import ClickHouseAgent
from agent.config import config

# Set API keys for all providers
config.set_model_api_key("openai", "your-openai-api-key")
config.set_model_api_key("anthropic", "your-anthropic-api-key")
config.set_model_api_key("google-gla", "your-google-api-key")

QUERIES = [
    ("openai:gpt-4o", "SHOW DATABASES"),
    ("anthropic:claude-3-sonnet-20240229", "SHOW TABLES"),
    ("google-gla:gemini-2.0-flash", "SHOW CLUSTERS"),
]


async def run_multi_query() -> None:
    agent = ClickHouseAgent()
    for model, query in QUERIES:
        result = await agent.run(model=model, query=query)
        print(f"Model: {model}")
        print("Analysis:", result.analysis)
        print("SQL Used:", result.sql_used)
        print("Confidence:", result.confidence)
        print("---")


if __name__ == "__main__":
    asyncio.run(run_multi_query())
