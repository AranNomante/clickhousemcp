"""Seed a ClickHouse server for tests/test_clickhouse_live.py.

Loads docker/init.sql into ``demo`` and adds a ``secret.salaries`` table used to check
what allow-lists do and do not restrict. Connection settings come from CLICKHOUSE_* env vars.
"""

import os
import time
from pathlib import Path

import clickhouse_connect

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    client = None
    for _ in range(30):
        try:
            client = clickhouse_connect.get_client(
                host=os.getenv("CLICKHOUSE_HOST", "localhost"),
                port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
                username=os.getenv("CLICKHOUSE_USER", "default"),
                password=os.getenv("CLICKHOUSE_PASSWORD", ""),
            )
            client.command("SELECT 1")
            break
        except Exception:
            time.sleep(2)
    if client is None:
        raise SystemExit("ClickHouse did not become ready")

    client.command("CREATE DATABASE IF NOT EXISTS demo")
    client.command("DROP TABLE IF EXISTS demo.orders")
    client.command("DROP TABLE IF EXISTS demo.products")
    sql = "\n".join(
        line for line in (ROOT / "docker" / "init.sql").read_text().splitlines() if not line.strip().startswith("--")
    )
    for statement in (s.strip() for s in sql.split(";")):
        if statement:
            client.command(statement)

    client.command("CREATE DATABASE IF NOT EXISTS secret")
    client.command("DROP TABLE IF EXISTS secret.salaries")
    client.command("CREATE TABLE secret.salaries (name String, salary UInt32) ENGINE = MergeTree ORDER BY name")
    client.command("INSERT INTO secret.salaries VALUES ('alice', 250000), ('bob', 180000)")
    print("Seeded demo.orders, demo.products, secret.salaries")


if __name__ == "__main__":
    main()
