import logging
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class EnvConfig:
    """Central configuration for AI and ClickHouse settings."""

    ai_model: str = "gemini-2.0-flash"
    log_level: str = "INFO"
    debug: bool = False

    clickhouse_host: str = "sql-clickhouse.clickhouse.com"
    clickhouse_port: str = "8443"
    clickhouse_user: str = "demo"
    clickhouse_password: str = ""
    clickhouse_secure: str = "true"

    def set_ai_model(self, model: str) -> None:
        self.ai_model = model
        logger.info(f"AI model set to: {model}")

    def set_log_level(self, level: str) -> None:
        self.log_level = level
        # Set log level for loggers within the application's namespace
        namespace = __name__.split('.')[0]  # Get the top-level package name
        for name in logging.root.manager.loggerDict:
            if name.startswith(namespace):
                logging.getLogger(name).setLevel(level)
        logger.info(f"Log level set to: {level} (applied to namespace '{namespace}')")

    def set_debug(self, debug: bool) -> None:
        self.debug = debug
        logger.info(f"Debug mode set to: {debug}")

    def set_clickhouse(
        self,
        host: Optional[str] = None,
        port: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        secure: Optional[str] = None,
    ) -> None:
        if host is not None:
            self.clickhouse_host = host
            logger.info(f"ClickHouse host set to: {host}")
        if port is not None:
            self.clickhouse_port = port
            logger.info(f"ClickHouse port set to: {port}")
        if user is not None:
            self.clickhouse_user = user
            logger.info(f"ClickHouse user set to: {user}")
        if password is not None:
            self.clickhouse_password = password
            logger.info("ClickHouse password updated.")
        if secure is not None:
            self.clickhouse_secure = secure
            logger.info(f"ClickHouse secure set to: {secure}")


config = EnvConfig()
"""Configuration management for ClickHouse connections."""


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
    def from_defaults(cls) -> "ClickHouseConfig":
        """Create config from default values only."""
        return cls(
            name="default",
            host="localhost",
            port="8443",
            user="default",
            password="",
            secure="true",
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
        configs = {"playground": cls.PLAYGROUND, "local": cls.LOCAL, "default": ClickHouseConfig.from_defaults()}
        return configs.get(name.lower())

    @classmethod
    def list_configs(cls) -> Dict[str, ClickHouseConfig]:
        """List all available configurations."""
        return {"playground": cls.PLAYGROUND, "local": cls.LOCAL, "default": ClickHouseConfig.from_defaults()}


def get_connection_string(config: ClickHouseConfig) -> str:
    """Generate a connection string for display purposes."""
    protocol = "https" if config.secure == "true" else "http"
    if config.password:
        return f"{protocol}://{config.user}:***@{config.host}:{config.port}"
    else:
        return f"{protocol}://{config.user}@{config.host}:{config.port}"
