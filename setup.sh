#!/bin/sh
# Creates a virtual environment and installs dependencies.
set -e
cd "$(dirname "$0")"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
mkdir -p data
echo ""
echo "Done. Next:"
echo "  source venv/bin/activate"
echo "  python pulse.py demo"
