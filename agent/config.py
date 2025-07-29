"""Configuration management for ClickHouse connections."""

import os
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ClickHouseConfig:
    """ClickHouse connection configuration."""

    name: str
    host: str
    port: str = "8443"
    user: str = "default"
    password: str = ""
    secure: str = "true"

    @classmethod
    def from_env(cls, prefix: str = "CLICKHOUSE") -> "ClickHouseConfig":
        """Create config from environment variables."""
        return cls(
            name="env",
            host=os.getenv(f"{prefix}_HOST", "localhost"),
            port=os.getenv(f"{prefix}_PORT", "8443"),
            user=os.getenv(f"{prefix}_USER", "default"),
            password=os.getenv(f"{prefix}_PASSWORD", ""),
            secure=os.getenv(f"{prefix}_SECURE", "true"),
        )


class ClickHouseConnections:
    """Predefined ClickHouse connection configurations."""

    PLAYGROUND = ClickHouseConfig(
        name="playground", host="sql-clickhouse.clickhouse.com", port="8443", user="demo", password="", secure="true"
    )

    LOCAL = ClickHouseConfig(name="local", host="localhost", port="9000", user="default", password="", secure="false")

    @classmethod
    def get_config(cls, name: str) -> Optional[ClickHouseConfig]:
        """Get a predefined configuration by name."""
        configs = {"playground": cls.PLAYGROUND, "local": cls.LOCAL, "env": ClickHouseConfig.from_env()}
        return configs.get(name.lower())

    @classmethod
    def list_configs(cls) -> Dict[str, ClickHouseConfig]:
        """List all available configurations."""
        return {"playground": cls.PLAYGROUND, "local": cls.LOCAL, "env": ClickHouseConfig.from_env()}


def get_connection_string(config: ClickHouseConfig) -> str:
    """Generate a connection string for display purposes."""
    protocol = "https" if config.secure == "true" else "http"
    if config.password:
        return f"{protocol}://{config.user}:***@{config.host}:{config.port}"
    else:
        return f"{protocol}://{config.user}@{config.host}:{config.port}"


if __name__ == "__main__":
    # Demo the configurations
    print("Available ClickHouse Configurations:")
    print("=" * 40)

    for name, config in ClickHouseConnections.list_configs().items():
        print(f"{name.upper()}:")
        print(f"  Connection: {get_connection_string(config)}")
        print(f"  Secure: {config.secure}")
        print()

    # Show environment-based config
    print("Environment Variables for Custom Config:")
    print("CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER,")
    print("CLICKHOUSE_PASSWORD, CLICKHOUSE_SECURE")
