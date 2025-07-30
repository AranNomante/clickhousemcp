"""
ClickHouse MCP Agent Server Cache.

This module provides caching mechanisms for the ClickHouse MCP agent,
improving performance and reducing short term server re-connections.
"""

from cachetools import TTLCache
from pydantic_ai.mcp import MCPServerStdio
import hashlib
from typing import Any, Optional, Set

import logging

logger = logging.getLogger(__name__)


class ServerTTLCache(TTLCache):
    """
    Custom TTLCache that ensures proper cleanup of server connections
    when items are deleted from the cache.
    """

    _pending_cleanup: Set[MCPServerStdio]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._pending_cleanup = set()
        logger.info(f"ServerTTLCache initialized with maxsize={self.maxsize}, ttl={self.ttl}")

    def __delitem__(self, key: str) -> None:
        server = self.get(key)
        if server and hasattr(server, "__aexit__"):
            self._pending_cleanup.add(server)
            logger.info(f"Server evicted from cache and marked for async cleanup: key={key}")
        else:
            logger.info(f"Server evicted from cache: key={key}")
        super().__delitem__(key)

    async def cleanup(self) -> None:
        logger.info(f"Starting async cleanup of {len(self._pending_cleanup)} server(s)")
        for server in self._pending_cleanup:
            await server.__aexit__()
            logger.info("Server async cleanup complete")
        self._pending_cleanup.clear()
        logger.info("All pending servers cleaned up")

    async def get_server(self, env: dict) -> MCPServerStdio:
        """
        Retrieve the server from the cache using env dict, initializing it if necessary.
        Hashes env to create a unique cache key.
        Checks if server is running, recreates if not.
        """
        env_str = str(sorted(env.items()))
        key = hashlib.sha256(env_str.encode()).hexdigest()
        server: Optional[MCPServerStdio] = self.get(key)

        if server and getattr(server, "is_running", False):
            logger.debug(f"Cache hit for server: key={key}")
        else:
            if server:
                logger.info(f"Cache miss or stale server, recreating: key={key}")
                if hasattr(server, "__aexit__"):
                    await server.__aexit__()
            else:
                logger.info(f"Cache miss, creating new server: key={key}")
            server = MCPServerStdio("mcp-clickhouse", args=[], env=env)
            self[key] = server
        return server
