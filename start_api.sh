#!/bin/bash
# Start script for FastAPI server

# Load virtual environment
source .venv/bin/activate

# Start FastAPI server
echo "Starting FastAPI server..."
uvicorn api:app --host 0.0.0.0 --port 8000 --reload