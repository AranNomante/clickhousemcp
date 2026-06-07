"""
Minimal example: Query local Docker ClickHouse with seeded demo data.

Prerequisites:
    docker compose up -d
    uv pip install -e ".[dev]"

Set your API key via environment variable or replace the placeholder below.
"""

import asyncio
import os
from agent.clickhouse_agent import ClickHouseAgent
from agent.config import config

config.set_log_level("INFO")

# Local ClickHouse running via docker-compose.yml
config.set_clickhouse(host="localhost", port="8123", user="default", password="", secure="false")

# AI provider — replace or set GOOGLE_API_KEY in your environment
config.set_ai_model(os.environ.get("AI_MODEL", "google:gemini-3.1-flash-lite"))
config.set_model_api_key("google", os.environ.get("GOOGLE_API_KEY", ""))


async def run_minimal() -> None:
    agent = ClickHouseAgent()
    result = await agent.run(
        allowed_tables=["orders", "products"],
        allowed_databases=["demo"],
        query="can you please give me some insights on the recent data?",
    )
    print(result.analysis)


if __name__ == "__main__":
    asyncio.run(run_minimal())
