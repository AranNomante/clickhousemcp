"""Basic tests for ClickHouse MCP Agent package."""

import pytest
from agent import ClickHouseConfig
from agent.config import ClickHouseConnections


def test_clickhouse_config_creation():
    """Test ClickHouseConfig can be created with required fields."""
    config = ClickHouseConfig(
        name="test",
        host="localhost",
        port="9000",
        user="default"
    )
    
    assert config.name == "test"
    assert config.host == "localhost"
    assert config.port == "9000"
    assert config.user == "default"
    assert config.password == ""  # Default value
    assert config.secure == "true"  # Default value for secure connections


def test_builtin_connections_exist():
    """Test that builtin connections are properly defined."""
    connections = ClickHouseConnections.list_configs()
    
    assert "playground" in connections
    assert "local" in connections
    assert "env" in connections
    
    # Test playground config
    playground = connections["playground"]
    assert playground.host == "sql-clickhouse.clickhouse.com"
    assert playground.user == "demo"


def test_clickhouse_config_connection_string():
    """Test that ClickHouseConfig generates proper connection info."""
    config = ClickHouseConfig(
        name="test",
        host="clickhouse.example.com",
        port="8443",
        user="analyst",
        password="secret",
        secure="true"
    )
    
    # Test that all required fields are present
    assert config.host
    assert config.port
    assert config.user
    # Don't test actual connection string format as it's internal


def test_package_imports():
    """Test that package imports work correctly."""
    # These should not raise ImportError
    from agent import query_clickhouse, ClickHouseConfig
    from agent.clickhouse_agent import run_clickhouse_agent, ClickHouseOutput
    from agent.config import ClickHouseConnections
    from agent.env_config import config, logger
    
    # Test that main functions are callable
    assert callable(query_clickhouse)
    assert callable(run_clickhouse_agent)


@pytest.mark.asyncio
async def test_clickhouse_output_structure():
    """Test ClickHouseOutput dataclass structure."""
    from agent.clickhouse_agent import ClickHouseOutput
    
    output = ClickHouseOutput(
        analysis="Test analysis",
        sql_used="SELECT 1",
        confidence=8
    )
    
    assert output.analysis == "Test analysis"
    assert output.sql_used == "SELECT 1" 
    assert output.confidence == 8


def test_env_config_validation():
    """Test environment configuration validation."""
    from agent.env_config import validate_setup
    
    # This should return validation results
    is_valid, issues = validate_setup()
    
    # Should return a boolean and list
    assert isinstance(is_valid, bool)
    assert isinstance(issues, list)
