#!/bin/bash
#
# E5 Diff-to-Test Planner - Setup Script
# Creates virtual environment and initializes databases
#

set -euo pipefail

PROJECT_NAME="e5-diff-to-test-planner"
VENV_DIR=".venv"
PYTHON_CMD="python3"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  E5 Diff-to-Test Planner Setup                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo

# Check Python version
echo "✓ Checking Python installation..."
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "✗ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "  Python version: $VERSION"
echo

# Create virtual environment
echo "✓ Creating virtual environment..."
if [ -d "$VENV_DIR" ]; then
    echo "  Reusing virtual environment at $VENV_DIR"
else
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "  Created: $VENV_DIR"
fi
echo

# Activate virtual environment
echo "✓ Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo "  Activated: $VENV_DIR"
echo

# Upgrade pip
echo "✓ Upgrading pip..."
pip install --upgrade pip setuptools wheel
echo "  Pip upgraded"
echo

# Install dependencies
echo "✓ Installing dependencies..."
pip install -r requirements.txt
echo "  Dependencies installed:"
pip list | grep -E "click|sentence-transformers|torch|numpy|scikit-learn|pydantic|fastapi" || true
echo

# Initialize databases
echo "✓ Initializing databases..."
$PYTHON_CMD << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '.')

from src.database import init_databases, verify_databases
from src.data_loader import DataLoader

try:
    init_databases()
    print("  Databases initialized successfully")
    
    # Load sample data
    print("\n  Loading sample data...")
    loader = DataLoader()
    results = loader.load_all()
    
    # Verify
    stats = verify_databases()
    print("\n  Database Statistics:")
    for table_name, count in stats.items():
        print(f"    • {table_name}: {count} records")
    
except Exception as e:
    print(f"  ✗ Error initializing databases: {e}")
    sys.exit(1)
PYTHON_SCRIPT

echo

# Run tests
echo "✓ Running tests..."
$PYTHON_CMD -m pytest tests/ -q --tb=short
echo

# Display next steps
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Setup Complete! 🎉                                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo
echo "✓ Virtual environment ready at: $VENV_DIR"
echo "✓ Dependencies installed"
echo "✓ Databases initialized"
echo "✓ Tests passing"
echo
echo "📌 Next steps:"
echo "   1. Activate environment: source $VENV_DIR/bin/activate"
echo "   2. Run analysis: python3 -m src.cli analyze --help"
echo "   3. Read docs: cat README.md"
echo

# Display activation hint for non-sourced execution
if [ "$BASH_SOURCE" == "$0" ]; then
    echo "⚠️  To activate the virtual environment, run:"
    echo "   source $VENV_DIR/bin/activate"
fi
