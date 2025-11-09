#!/bin/bash
# Start script for Celery worker

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Load virtual environment
source .venv/bin/activate

# Start Celery worker
echo "Starting Celery worker..."
echo "Using Redis: ${REDIS_URL:-redis://localhost:6379/0}"
celery -A celery_config worker --loglevel=info --concurrency=4
