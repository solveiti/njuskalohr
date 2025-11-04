#!/bin/bash
# Start script for Celery worker

# Load virtual environment
source .venv/bin/activate

# Start Celery worker
echo "Starting Celery worker..."
celery -A celery_config worker --loglevel=info --concurrency=4
