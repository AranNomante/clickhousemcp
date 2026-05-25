"""
Stream example: Query local Docker ClickHouse with seeded demo data.

Prerequisites:
    docker compose up -d
    uv pip install -e ".[dev]"

Set your API key via environment variable or replace the placeholder below.
"""

import asyncio
import os
from agent.clickhouse_agent import ClickHouseAgent, logger
from agent.config import config, summarize_config

config.set_log_level("INFO")

# Local ClickHouse running via docker-compose.yml
config.set_clickhouse(host="localhost", port="8123", user="default", password="", secure="false")

# Summarization (optional — uses a cheap model to prune long histories)
summarize_config.set_token_limit(10000)
summarize_config.set_ai_model("gemini-2.5-flash")

# AI provider — replace or set GEMINI_API_KEY in your environment
config.set_ai_model("gemini-2.5-flash")
config.set_model_api_key("google", os.environ.get("GOOGLE_API_KEY",""))


async def run_stream() -> None:
    agent = ClickHouseAgent()
    async for chunk in agent.run_stream(
        allowed_tables=["orders", "products"],
        allowed_databases=["demo"],
        query="can you please give me some insights on my data?",
    ):
        logger.info("received chunk %s", chunk)


if __name__ == "__main__":
    asyncio.run(run_stream())
