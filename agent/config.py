import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Model-string prefixes (``"<prefix>:<model>"``) that map to a different provider name.
_PREFIX_ALIASES = {
    "google-gla": "google",
    "google-vertex": "google",
    "gemini": "google",
    "openai-chat": "openai",
    "openai-responses": "openai",
    "cohere": "co",
}


def _bool_str(value: str | bool | None) -> str | None:
    """Accept True/False as well as the "true"/"false" strings mcp-clickhouse reads."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def provider_from_model(model: str) -> str | None:
    """Return the provider for a ``"<prefix>:<model>"`` string, or None if it has no known prefix."""
    if ":" not in model:
        return None
    prefix = model.split(":", 1)[0].lower()
    provider = _PREFIX_ALIASES.get(prefix, prefix)
    return provider if hasattr(ModelAPIConfig, f"{provider.upper()}_API_KEY") else None


def apply_api_key(model_api: "ModelAPIConfig", provider: str) -> bool:
    """Export the configured key for ``provider`` to its env var.

    A key set via ``set_model_api_key`` overrides any existing env var. Returns False only
    when ``provider`` is a known keyed provider and no key is available at all.
    """
    attr = f"{provider.upper()}_API_KEY"
    if not hasattr(model_api, attr):
        return True  # unknown provider (e.g. a local model); nothing to check
    key = getattr(model_api, attr)
    if key:
        os.environ[attr] = key
        return True
    return bool(os.environ.get(attr))


@dataclass
class ModelAPIConfig:
    """Configuration for all supported model API keys."""

    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    GROK_API_KEY: str | None = None  # legacy `grok:` prefix; prefer XAI_API_KEY with `xai:`
    XAI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    MISTRAL_API_KEY: str | None = None
    CO_API_KEY: str | None = None

    def set_api_key(self, provider: str, key: str) -> None:
        provider_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "grok": "GROK_API_KEY",
            "xai": "XAI_API_KEY",
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


@dataclass
class EnvConfig:
    """Central configuration for AI, model provider, and ClickHouse settings."""

    ai_model: str = "google:gemini-3.1-flash-lite"
    model_provider: str = "google"  # Default provider
    log_level: str = "INFO"
    debug: bool = False

    clickhouse_host: str = "sql-clickhouse.clickhouse.com"
    clickhouse_port: str = "8443"
    clickhouse_user: str = "demo"
    clickhouse_password: str = ""
    clickhouse_secure: str = "true"

    # Optional mcp-clickhouse settings; None leaves the server's default in place.
    clickhouse_database: str | None = None
    clickhouse_role: str | None = None
    clickhouse_verify: str | None = None
    clickhouse_connect_timeout: int | None = None
    clickhouse_send_receive_timeout: int | None = None
    clickhouse_query_timeout: int | None = None

    model_api: ModelAPIConfig = field(default_factory=ModelAPIConfig)

    def set_ai_model(self, model: str) -> None:
        self.ai_model = model
        logger.info(f"AI model set to: {model}")
        provider = provider_from_model(model)
        if provider is not None:
            self.set_model_provider(provider)

    def set_model_provider(self, provider: str) -> None:
        self.model_provider = provider
        logger.info(f"Model provider set to: {provider}")

    def mcp_server_env(self) -> dict[str, str]:
        """Environment variables passed to the mcp-clickhouse subprocess."""
        env = {
            "CLICKHOUSE_HOST": self.clickhouse_host,
            "CLICKHOUSE_PORT": self.clickhouse_port,
            "CLICKHOUSE_USER": self.clickhouse_user,
            "CLICKHOUSE_PASSWORD": self.clickhouse_password,
            "CLICKHOUSE_SECURE": self.clickhouse_secure,
        }
        optional: dict[str, str | int | None] = {
            "CLICKHOUSE_DATABASE": self.clickhouse_database,
            "CLICKHOUSE_ROLE": self.clickhouse_role,
            "CLICKHOUSE_VERIFY": self.clickhouse_verify,
            "CLICKHOUSE_CONNECT_TIMEOUT": self.clickhouse_connect_timeout,
            "CLICKHOUSE_SEND_RECEIVE_TIMEOUT": self.clickhouse_send_receive_timeout,
            "CLICKHOUSE_MCP_QUERY_TIMEOUT": self.clickhouse_query_timeout,
        }
        env.update({k: str(v) for k, v in optional.items() if v is not None})
        return env

    def set_log_level(self, level: str) -> None:
        # Normalize and validate the provided level name.
        level_name = (level or "").upper()
        numeric = getattr(logging, level_name, None)
        if numeric is None:
            logger.warning("Unknown log level '%s', defaulting to INFO", level)
            numeric = logging.INFO
            level_name = "INFO"

        self.log_level = level_name

        # Apply level to package loggers only — libraries must not touch root logger handlers.
        namespace = __name__.split(".")[0]
        for name in logging.root.manager.loggerDict:
            if name.startswith(namespace):
                logging.getLogger(name).setLevel(numeric)

        logger.info(f"Log level set to: {level_name} (applied to namespace '{namespace}')")

    def set_debug(self, debug: bool) -> None:
        self.debug = debug
        logger.info(f"Debug mode set to: {debug}")

    def set_clickhouse(
        self,
        host: str | None = None,
        port: str | int | None = None,
        user: str | None = None,
        password: str | None = None,
        secure: str | bool | None = None,
        *,
        database: str | None = None,
        role: str | None = None,
        verify: str | bool | None = None,
        connect_timeout: int | None = None,
        send_receive_timeout: int | None = None,
        query_timeout: int | None = None,
    ) -> None:
        """Set ClickHouse connection options. Arguments left as None are unchanged.

        ``role`` is a ClickHouse role applied to the session (server-side access control).
        ``query_timeout`` is mcp-clickhouse's SELECT timeout in seconds (server default 30).
        """
        port = str(port) if port is not None else None
        secure = _bool_str(secure)
        optional: dict[str, str | int | None] = {
            "database": database,
            "role": role,
            "verify": _bool_str(verify),
            "connect_timeout": connect_timeout,
            "send_receive_timeout": send_receive_timeout,
            "query_timeout": query_timeout,
        }
        for name, value in optional.items():
            if value is not None:
                setattr(self, f"clickhouse_{name}", value)
                logger.info(f"ClickHouse {name} set to: {value}")
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

    def use_connection(self, connection: "ClickHouseConfig | str") -> None:
        """Apply a ClickHouse connection: a ``ClickHouseConfig`` or a preset name ("playground", "local")."""
        if isinstance(connection, str):
            preset = ClickHouseConnections.get_config(connection)
            if preset is None:
                raise ValueError(f"Unknown connection preset: {connection!r}")
            connection = preset
        self.set_clickhouse(
            host=connection.host,
            port=connection.port,
            user=connection.user,
            password=connection.password,
            secure=connection.secure,
        )


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

    LOCAL = ClickHouseConfig(name="local", host="localhost", port="8123", user="default", password="", secure="false")

    @classmethod
    def get_config(cls, name: str) -> ClickHouseConfig | None:
        """Get a predefined configuration by name."""
        configs = {"playground": cls.PLAYGROUND, "local": cls.LOCAL, "default": ClickHouseConfig.from_defaults()}
        return configs.get(name.lower())

    @classmethod
    def list_configs(cls) -> dict[str, ClickHouseConfig]:
        """List all available configurations."""
        return {"playground": cls.PLAYGROUND, "local": cls.LOCAL, "default": ClickHouseConfig.from_defaults()}


def get_connection_string(config: ClickHouseConfig) -> str:
    """Generate a connection string for display purposes."""
    protocol = "https" if config.secure == "true" else "http"
    if config.password:
        return f"{protocol}://{config.user}:***@{config.host}:{config.port}"
    else:
        return f"{protocol}://{config.user}@{config.host}:{config.port}"


@dataclass
class SummarizeAgentEnv:
    """Minimal config for the summarization agent (no ClickHouse fields)."""

    ai_model: str = "google:gemini-3.1-flash-lite"
    model_provider: str = "google"  # Default provider
    model_api: ModelAPIConfig = field(default_factory=ModelAPIConfig)
    # Context size (tokens) above which history is summarized. Tool definitions and
    # instructions alone are ~600 tokens per request, so low values summarize every turn.
    token_limit: int = 50_000

    def set_ai_model(self, model: str) -> None:
        self.ai_model = model
        logger.info(f"AI model set to: {model}")
        provider = provider_from_model(model)
        if provider is not None:
            self.set_model_provider(provider)

    def set_model_provider(self, provider: str) -> None:
        self.model_provider = provider
        logger.info(f"Model provider set to: {provider}")

    def set_model_api_key(self, provider: str, key: str) -> None:
        self.set_model_provider(provider)
        self.model_api.set_api_key(provider, key)

    def set_token_limit(self, limit: int) -> None:
        self.token_limit = limit
        logger.info(f"Token limit set to: {limit}")


summarize_config = SummarizeAgentEnv()
