import logging
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ModelAPIConfig:
    """Configuration for all supported model API keys."""

    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    CO_API_KEY: Optional[str] = None

    def set_api_key(self, provider: str, key: str) -> None:
        provider_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "groq": "GROQ_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "co": "CO_API_KEY",
        }
        attr = provider_map.get(provider.lower())
        if attr:
            setattr(self, attr, key)
            logger.info(f"Set API key for {provider}.")
        else:
            logger.warning(f"Unknown provider: {provider}")


logger = logging.getLogger(__name__)


@dataclass
class EnvConfig:
    """Central configuration for AI, model provider, and ClickHouse settings."""

    ai_model: str = "gemini-2.0-flash"
    model_provider: str = "google"  # Default provider
    log_level: str = "INFO"
    debug: bool = False

    clickhouse_host: str = "sql-clickhouse.clickhouse.com"
    clickhouse_port: str = "8443"
    clickhouse_user: str = "demo"
    clickhouse_password: str = ""
    clickhouse_secure: str = "true"

    model_api: ModelAPIConfig = field(default_factory=ModelAPIConfig)

    def set_ai_model(self, model: str) -> None:
        self.ai_model = model
        logger.info(f"AI model set to: {model}")

    def set_model_provider(self, provider: str) -> None:
        self.model_provider = provider
        logger.info(f"Model provider set to: {provider}")

    def set_log_level(self, level: str) -> None:
        self.log_level = level
        # Set log level for loggers within the application's namespace
        namespace = __name__.split(".")[0]  # Get the top-level package name
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

    def set_model_api_key(self, provider: str, key: str) -> None:
        self.set_model_provider(provider)
        self.model_api.set_api_key(provider, key)


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
    model_provider: str = "google"  # Default provider

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
            model_provider="google",
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
