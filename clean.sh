#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧹 Cleaning ClickHouse MCP Agent...${NC}"

# Remove virtual environment
if [ -d ".venv" ]; then
    echo -e "${YELLOW}🗑️  Removing virtual environment...${NC}"
    rm -rf .venv
fi

# Remove Python cache files
echo -e "${YELLOW}🗑️  Removing Python cache files...${NC}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# Remove build artifacts
if [ -d "clickhouse_mcp_agent.egg-info" ]; then
    echo -e "${YELLOW}🗑️  Removing build artifacts...${NC}"
    rm -rf clickhouse_mcp_agent.egg-info
fi

if [ -d "build" ]; then
    rm -rf build
fi

if [ -d "dist" ]; then
    rm -rf dist
fi

# Remove UV lock file
if [ -f "uv.lock" ]; then
    echo -e "${YELLOW}🗑️  Removing UV lock file...${NC}"
    rm -f uv.lock
fi

echo -e "${GREEN}✅ Cleanup complete!${NC}"
echo -e "${BLUE}💡 Run ./setup.sh to reinstall${NC}"

# Remove mypy and pytest cache
find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

