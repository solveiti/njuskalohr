#!/bin/bash
# Start all services for the Njuskalo scraper API

# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis server..."
    redis-server --daemonize yes
    sleep 2
fi

# Load virtual environment
source .venv/bin/activate

echo "Starting all Njuskalo scraper services..."

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A celery_config worker --loglevel=info --concurrency=4 --detach --pidfile=celery_worker.pid --logfile=celery_worker.log

# Start Celery beat in background
echo "Starting Celery beat scheduler..."
celery -A celery_config beat --loglevel=info --detach --pidfile=celery_beat.pid --logfile=celery_beat.log

# Give Celery services time to start
sleep 3

# Start FastAPI server (foreground)
echo "Starting FastAPI server..."
echo "Dashboard will be available at: http://localhost:8000"
echo "API documentation will be available at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Trap SIGINT to stop all services
trap 'echo "Stopping services..."; pkill -F celery_worker.pid; pkill -F celery_beat.pid; exit' INT

uvicorn api:app --host 0.0.0.0 --port 8000 --reload