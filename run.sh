#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ Virtual environment not found. Run ./setup.sh first.${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating from template...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}📝 Please edit .env and add your GOOGLE_API_KEY${NC}"
    else
        echo -e "${RED}❌ .env.example not found.${NC}"
        exit 1
    fi
fi

echo -e "${BLUE}🚀 Starting ClickHouse MCP Agent...${NC}"

# Activate virtual environment
source .venv/bin/activate

# Run the CLI command (defined in pyproject.toml)
echo -e "${BLUE}🔌 Activating environment and starting agent...${NC}"
if ! clickhouse-mcp-demo; then
    echo -e "${RED}❌ Agent execution failed. Check your .env configuration.${NC}"
    echo -e "${YELLOW}💡 Make sure GOOGLE_API_KEY is set in .env${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Agent completed successfully${NC}"
