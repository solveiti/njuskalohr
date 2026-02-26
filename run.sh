#!/bin/bash
# Njuskalo Scraper launcher
#
# Requires: the remote server's VNC display :3 must already be running.
# Firefox will be directed at DISPLAY=:3 automatically.
#
# Usage (inside a screen session):
#   screen -S scraper
#   ./run.sh                         # full scrape with tunnels
#   ./run.sh --mode enhanced         # enhanced scrape, no tunnels
#   ./run.sh --mode basic            # basic sitemap scrape
#   ./run.sh --max-stores 10         # test run, limit to 10 stores
#   ./run.sh --no-tunnels            # disable SSH tunnels
#   ./run.sh --no-database           # skip DB/Excel, print results only
#   ./run.sh --verbose               # debug logging
#
# Detach from screen: Ctrl+A then D
# Reattach:          screen -r scraper

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Warning: .venv not found, using system Python"
fi

# Load environment variables
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Point Firefox at the VNC display defined in .env (DISPLAY_NUM, default :3).
# The display must already be running on the remote server.
if [ -z "$DISPLAY" ]; then
    export DISPLAY="${DISPLAY_NUM:-:3}"
fi

exec python run_scraper.py "$@"
