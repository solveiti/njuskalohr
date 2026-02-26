#!/bin/bash
# Njuskalo Scraper launcher
#
# Requires: the remote server's VNC display :3 must already be running.
# Firefox will be directed at DISPLAY=:3 automatically.
#
# Usage:
#   ./run.sh                         # start detached (default)
#   ./run.sh --foreground            # run in current terminal
#   ./run.sh --status                # show detached process status
#   ./run.sh --stop                  # stop detached process
#
# Scraper options are forwarded to run_scraper.py, for example:
#   ./run.sh --mode enhanced
#   ./run.sh --max-stores 10
#   ./run.sh --no-tunnels
#   ./run.sh --no-database
#   ./run.sh --verbose

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DETACH_ENABLED=true
RUN_LOG_DIR="${RUN_LOG_DIR:-$SCRIPT_DIR/logs}"
RUN_LOG_FILE="${RUN_LOG_FILE:-$RUN_LOG_DIR/scraper.log}"
RUN_PID_FILE="${RUN_PID_FILE:-$RUN_LOG_DIR/scraper.pid}"
FORWARDED_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --foreground)
            DETACH_ENABLED=false
            shift
            ;;
        --status)
            mkdir -p "$RUN_LOG_DIR"
            if [[ -f "$RUN_PID_FILE" ]]; then
                PID="$(cat "$RUN_PID_FILE")"
                if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
                    echo "Scraper is running (PID: $PID)"
                    echo "Log file: $RUN_LOG_FILE"
                    exit 0
                else
                    echo "Stale PID file found, cleaning up: $RUN_PID_FILE"
                    rm -f "$RUN_PID_FILE"
                fi
            fi
            echo "Scraper is not running"
            exit 1
            ;;
        --stop)
            if [[ -f "$RUN_PID_FILE" ]]; then
                PID="$(cat "$RUN_PID_FILE")"
                if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
                    kill "$PID"
                    rm -f "$RUN_PID_FILE"
                    echo "Stopped scraper process (PID: $PID)"
                    exit 0
                fi
                rm -f "$RUN_PID_FILE"
            fi
            echo "No running scraper process found"
            exit 1
            ;;
        --help)
            cat <<'EOF'
Usage: ./run.sh [launcher-options] [scraper-options]

Launcher options:
  --foreground          Run in current terminal (default is detached)
  --status              Show detached process status
  --stop                Stop detached process

Scraper options (forwarded):
  --mode {tunnel,enhanced,basic}
  --max-stores N
  --no-tunnels
  --no-database
  --verbose
    --headless

Examples:
  ./run.sh
  ./run.sh --mode enhanced
  ./run.sh --foreground --max-stores 10 --verbose
  ./run.sh --status
  ./run.sh --stop
EOF
            exit 0
            ;;
        *)
            FORWARDED_ARGS+=("$1")
            shift
            ;;
    esac
done

if [[ "$DETACH_ENABLED" == true ]]; then
    mkdir -p "$RUN_LOG_DIR"

    if [[ -f "$RUN_PID_FILE" ]]; then
        EXISTING_PID="$(cat "$RUN_PID_FILE")"
        if [[ -n "$EXISTING_PID" ]] && kill -0 "$EXISTING_PID" 2>/dev/null; then
            echo "Scraper already running (PID: $EXISTING_PID)"
            echo "Log file: $RUN_LOG_FILE"
            echo "Use: ./run.sh --status"
            exit 0
        fi
        rm -f "$RUN_PID_FILE"
    fi

    nohup "$SCRIPT_DIR/run.sh" --foreground "${FORWARDED_ARGS[@]}" >> "$RUN_LOG_FILE" 2>&1 < /dev/null &
    NEW_PID=$!
    echo "$NEW_PID" > "$RUN_PID_FILE"

    echo "Started detached scraper process (PID: $NEW_PID)"
    echo "Log file: $RUN_LOG_FILE"
    echo "Status: ./run.sh --status"
    echo "Stop:   ./run.sh --stop"
    exit 0
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
# Always prefer DISPLAY_NUM to avoid inheriting SSH/X11-forwarded DISPLAY values.
if [ -n "${DISPLAY_NUM:-}" ]; then
    export DISPLAY="$DISPLAY_NUM"
else
    export DISPLAY="${DISPLAY:-:3}"
fi

exec python run_scraper.py "${FORWARDED_ARGS[@]}"
