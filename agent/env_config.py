"""Environment configuration management with .env support."""

import os
import logging
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class EnvConfig:
    """Central configuration loaded from environment variables."""

    # AI Configuration
    google_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    ai_model: str = "gemini-2.0-flash"

    # ClickHouse Configuration
    clickhouse_host: str = "sql-clickhouse.clickhouse.com"
    clickhouse_port: str = "8443"
    clickhouse_user: str = "demo"
    clickhouse_password: str = ""
    clickhouse_secure: str = "true"

    # Development Configuration
    log_level: str = "INFO"
    debug: bool = False

    def __post_init__(self) -> None:
        """Load values from environment variables."""
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.ai_model = os.getenv("AI_MODEL", self.ai_model)

        self.clickhouse_host = os.getenv("CLICKHOUSE_HOST", self.clickhouse_host)
        self.clickhouse_port = os.getenv("CLICKHOUSE_PORT", self.clickhouse_port)
        self.clickhouse_user = os.getenv("CLICKHOUSE_USER", self.clickhouse_user)
        self.clickhouse_password = os.getenv("CLICKHOUSE_PASSWORD", self.clickhouse_password)
        self.clickhouse_secure = os.getenv("CLICKHOUSE_SECURE", self.clickhouse_secure)

        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.debug = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")

    @property
    def api_key(self) -> Optional[str]:
        """Get the first available API key."""
        return self.google_api_key or self.gemini_api_key

    @property
    def has_api_key(self) -> bool:
        """Check if any API key is available."""
        return bool(self.api_key)

    def setup_logging(self) -> None:
        """Configure logging based on environment settings."""
        level = getattr(logging, self.log_level.upper(), logging.INFO)
        logging.basicConfig(level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


# Global configuration instance
config = EnvConfig()

# Set up logging
config.setup_logging()

# Create logger for this module
logger = logging.getLogger(__name__)

if config.debug:
    logger.debug("Environment configuration loaded")
    logger.debug(f"API key available: {config.has_api_key}")
    logger.debug(f"ClickHouse host: {config.clickhouse_host}")


def validate_setup() -> tuple[bool, list[str]]:
    """Validate that the environment is properly set up."""
    issues = []

    if not config.has_api_key:
        issues.append("No API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY")

    return len(issues) == 0, issues
