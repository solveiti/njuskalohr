#!/bin/bash
# Start script for Celery beat scheduler

# Load virtual environment
source .venv/bin/activate

# Start Celery beat
echo "Starting Celery beat scheduler..."
celery -A celery_config beat --loglevel=info