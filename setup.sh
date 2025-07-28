#!/bin/bash
# execute clean.sh before running this script


# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up ClickHouse MCP Agent...${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv .venv
else
    echo -e "${YELLOW}📦 Virtual environment already exists.${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}🔌 Activating virtual environment...${NC}"
source .venv/bin/activate

# Upgrade pip and install package
echo -e "${YELLOW}📥 Installing package...${NC}"
pip install --upgrade pip
pip install -e .

# Deactivate virtual environment
deactivate

echo -e "${GREEN}✅ Setup complete!${NC}"
echo
echo -e "${BLUE}📝 Next steps:${NC}"
echo -e "  1. Configure .env: ${YELLOW}cp .env.example .env${NC} (add your GOOGLE_API_KEY)"
echo -e "  2. Run project: ${YELLOW}./run.sh${NC}"
