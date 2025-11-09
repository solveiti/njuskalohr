#!/bin/bash
# Start script for Celery beat scheduler

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Load virtual environment
source .venv/bin/activate

# Start Celery beat
echo "Starting Celery beat scheduler..."
echo "Using Redis: ${REDIS_URL:-redis://localhost:6379/0}"
celery -A celery_config beat --loglevel=info