# Installation

## Quick Setup

```bash
./setup.sh               # Creates .venv and installs package
cp .env.example .env      # Configure environment (add GOOGLE_API_KEY)
./run.sh                 # Run the project
```

## Manual Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
deactivate
```

## Development Setup

```bash
git clone https://github.com/AranNomante/clickhousemcp.git
cd clickhousemcp
./setup.sh
source .venv/bin/activate
pip install -e ".[dev]"
```

All dependencies (including UV) are handled automatically by pyproject.toml.
