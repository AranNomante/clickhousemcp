"""Basic tests for ClickHouse MCP Agent package."""

import pytest
from agent import ClickHouseConfig
from agent.config import ClickHouseConnections


def test_clickhouse_config_creation() -> None:
    """Test ClickHouseConfig can be created with required fields."""
    config = ClickHouseConfig(name="test", host="localhost", port="9000", user="default")
    # Check all fields
    assert config.name == "test"
    assert config.host == "localhost"
    assert config.port == "9000"
    assert config.user == "default"
    assert config.password == ""  # Default value
    assert config.secure == "true"  # Default value for secure connections
    # Negative case: wrong user
    assert config.user != "admin"


def test_builtin_connections_exist() -> None:
    """Test that builtin connections are properly defined."""
    connections = ClickHouseConnections.list_configs()
    # Check all expected configs
    for key in ["playground", "local", "default"]:
        assert key in connections
    # Test playground config
    playground = connections["playground"]
    assert playground.host == "sql-clickhouse.clickhouse.com"
    assert playground.user == "demo"
    # Test local config
    local = connections["local"]
    assert local.host == "localhost"
    assert local.port == "9000"
    # Test default config
    default = connections["default"]
    assert default.host == "localhost"
    assert default.user == "default"


def test_clickhouse_config_connection_string() -> None:
    """Test that ClickHouseConfig generates proper connection info."""
    config = ClickHouseConfig(
        name="test", host="clickhouse.example.com", port="8443", user="analyst", password="secret", secure="true"
    )
    # Test that all required fields are present and correct
    assert config.host == "clickhouse.example.com"
    assert config.port == "8443"
    assert config.user == "analyst"
    assert config.password == "secret"
    assert config.secure == "true"
    # Test connection string format
    from agent.config import get_connection_string

    conn_str = get_connection_string(config)
    assert conn_str.startswith("https://analyst:***@clickhouse.example.com:8443")
    # Test without password
    config2 = ClickHouseConfig(name="nopass", host="host", user="u", port="9000", password="", secure="false")
    conn_str2 = get_connection_string(config2)
    assert conn_str2.startswith("http://u@host:9000")


def test_agent_instantiation_and_run_signature() -> None:
    """Test that ClickHouseAgent can be instantiated and has a run method."""
    from agent.clickhouse_agent import ClickHouseAgent

    agent = ClickHouseAgent()
    assert hasattr(agent, "run")
    # Check run method signature (async)
    import inspect

    assert inspect.iscoroutinefunction(agent.run)


def test_get_config_negative_case() -> None:
    """Test that requesting a non-existent config returns None."""
    from agent.config import ClickHouseConnections

    assert ClickHouseConnections.get_config("nonexistent") is None


def test_clickhouse_config_edge_cases() -> None:
    """Test edge cases for ClickHouseConfig creation."""
    from agent import ClickHouseConfig

    # Missing optional fields
    config = ClickHouseConfig(name="edge", host="host")
    assert config.port == "8443"  # Default
    assert config.user == "default"  # Default
    assert config.password == ""  # Default
    assert config.secure == "true"  # Default


@pytest.mark.asyncio
async def test_clickhouse_output_structure() -> None:
    """Test ClickHouseOutput dataclass structure."""
    from agent.clickhouse_agent import ClickHouseOutput

    # Test all fields and types
    output = ClickHouseOutput(analysis="Test analysis", confidence=8)
    assert isinstance(output.analysis, str)
    assert isinstance(output.confidence, int)
    assert output.analysis == "Test analysis"
    assert output.confidence == 8
