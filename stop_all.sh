#!/bin/bash
# Stop all services for the Njuskalo scraper API

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

echo "All services stopped."