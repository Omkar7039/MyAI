#!/bin/bash
set -e

echo "Installing MyAI..."

python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

echo ""
echo "MyAI installation complete."
echo "Run:"
echo "  source .venv/bin/activate"
echo "  python main.py"
