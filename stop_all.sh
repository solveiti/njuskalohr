#!/bin/bash
# Stop all services for the Njuskalo scraper API

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default values if not found in .env
API_HOST=${API_HOST:-0.0.0.0}
API_PORT=${API_PORT:-8080}

echo "Stopping all Njuskalo scraper services..."

# Stop Celery worker
if [ -f celery_worker.pid ]; then
    echo "Stopping Celery worker..."
    pkill -F celery_worker.pid
    rm -f celery_worker.pid
fi

# Stop Celery beat
if [ -f celery_beat.pid ]; then
    echo "Stopping Celery beat..."
    pkill -F celery_beat.pid
    rm -f celery_beat.pid
fi

# Stop any remaining Celery processes
pkill -f "celery.*celery_config"

# Stop FastAPI (if running in background)
pkill -f "python api.py"
pkill -f "uvicorn api:app"
# Also stop any FastAPI process on the configured port
if command -v lsof >/dev/null 2>&1; then
    lsof -ti:${API_PORT} | xargs kill -9 2>/dev/null || true
fi

echo "All services stopped (including port ${API_PORT})."