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
#
# By default, if this script is started outside a screen session,
# it will relaunch itself in a detached screen session automatically.
# Use --no-screen to disable this behavior.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Auto-run in detached screen unless already in screen or explicitly disabled
SCREEN_ENABLED=true
SCREEN_SESSION_NAME="${SCREEN_SESSION_NAME:-njuskalo}"
SCREEN_LOG_DIR="${SCREEN_LOG_DIR:-$SCRIPT_DIR/logs}"
SCREEN_LOG_FILE="${SCREEN_LOG_FILE:-$SCREEN_LOG_DIR/screen-${SCREEN_SESSION_NAME}.log}"
FORWARDED_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-screen)
            SCREEN_ENABLED=false
            shift
            ;;
        --screen-session)
            shift
            if [[ -n "${1:-}" ]]; then
                SCREEN_SESSION_NAME="$1"
                shift
            else
                echo "Error: --screen-session requires a value"
                exit 1
            fi
            ;;
        *)
            FORWARDED_ARGS+=("$1")
            shift
            ;;
    esac
done

if [[ "$SCREEN_ENABLED" == true && -z "${STY:-}" ]]; then
    if command -v screen >/dev/null 2>&1; then
        EXISTING_SESSION_ID="$(screen -ls | awk '/\.[[:alnum:]_-]+[[:space:]]/ {print $1}' | awk -F. -v name="$SCREEN_SESSION_NAME" '$2==name {print $0; exit}')"

        if [[ -n "$EXISTING_SESSION_ID" ]]; then
            echo "Screen session already running: $EXISTING_SESSION_ID"
            echo "Attach with: screen -d -r $SCREEN_SESSION_NAME"
            exit 0
        fi

        ESCAPED_ARGS=""
        for arg in "${FORWARDED_ARGS[@]}"; do
            ESCAPED_ARGS+=" $(printf '%q' "$arg")"
        done

        ESCAPED_SCRIPT_DIR="$(printf '%q' "$SCRIPT_DIR")"
        SCREEN_CMD="cd ${ESCAPED_SCRIPT_DIR} && ./run.sh --no-screen${ESCAPED_ARGS}"

        mkdir -p "$SCREEN_LOG_DIR"

        screen -L -Logfile "$SCREEN_LOG_FILE" -dmS "$SCREEN_SESSION_NAME" bash -lc "$SCREEN_CMD"
        NEW_SESSION_ID="$(screen -ls | awk '/\.[[:alnum:]_-]+[[:space:]]/ {print $1}' | awk -F. -v name="$SCREEN_SESSION_NAME" '$2==name {print $0; exit}')"
        if [[ -n "$NEW_SESSION_ID" ]]; then
            echo "Started detached screen session: $SCREEN_SESSION_NAME"
            echo "Attach with: screen -d -r $SCREEN_SESSION_NAME"
            echo "Log file: $SCREEN_LOG_FILE"
        else
            echo "Screen session ended quickly or failed to start"
            echo "Check log file: $SCREEN_LOG_FILE"
            echo "Run without screen for debugging: ./run.sh --no-screen"
        fi
        exit 0
    else
        echo "Warning: screen is not installed, running in foreground"
    fi
fi

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

exec python run_scraper.py "${FORWARDED_ARGS[@]}"
