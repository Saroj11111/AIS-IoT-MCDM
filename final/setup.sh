#!/usr/bin/env bash
# Initial setup for macOS / Linux
# Creates a virtual environment in .venv and installs the required packages.
set -e
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi
echo "Using $($PY --version)"

$PY -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo
echo "Setup complete. Checking the installation..."
python check_setup.py
echo
echo "Next time, activate the environment first:  source .venv/bin/activate"
echo "Then run, for example:                      python \"Final ranking.py\""
echo "Web frontend:                               python run_frontend.py"
