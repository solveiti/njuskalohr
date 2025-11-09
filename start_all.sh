#!/bin/bash
# Start all services for the Njuskalo scraper API

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default values if not found in .env
API_HOST=${API_HOST:-0.0.0.0}
API_PORT=${API_PORT:-8080}

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
celery -A celery_config worker --loglevel=info --concurrency=4 --detach --pidfile=celery_worker.pid --logfile=logs/celery_worker.log

# Start Celery beat in background
echo "Starting Celery beat scheduler..."
celery -A celery_config beat --loglevel=info --detach --pidfile=celery_beat.pid --logfile=logs/celery_beat.log

# Give Celery services time to start
sleep 3

# Start FastAPI server (foreground)
echo "Starting FastAPI server..."
echo "Dashboard will be available at: http://${API_HOST}:${API_PORT}"
echo "API documentation will be available at: http://${API_HOST}:${API_PORT}/docs"
echo ""
echo "Using configuration from .env:"
echo "  Host: ${API_HOST}"
echo "  Port: ${API_PORT}"
echo ""
echo "Press Ctrl+C to stop all services"

# Trap SIGINT to stop all services
trap 'echo "Stopping services..."; pkill -F celery_worker.pid; pkill -F celery_beat.pid; exit' INT

uvicorn api:app --host ${API_HOST} --port ${API_PORT} --reload
