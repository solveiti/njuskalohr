#!/bin/bash
# Start script for FastAPI server

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default values if not found in .env
API_HOST=${API_HOST:-0.0.0.0}
API_PORT=${API_PORT:-8080}

# Load virtual environment
source .venv/bin/activate

# Start FastAPI server
echo "Starting FastAPI server..."
echo "Server will be available at: http://${API_HOST}:${API_PORT}"
echo "Using configuration from .env:"
echo "  Host: ${API_HOST}"
echo "  Port: ${API_PORT}"
echo ""
uvicorn api:app --host ${API_HOST} --port ${API_PORT} --reload