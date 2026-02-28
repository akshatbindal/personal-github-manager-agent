#!/bin/bash
# Enable unbuffered output for Python
export PYTHONUNBUFFERED=1

echo "Starting Personal GitHub Manager Agent API..."

# Start the unified FastAPI application
# We use exec so uvicorn receives termination signals correctly
port=${PORT:-8080}
exec uvicorn src.main:app --host 0.0.0.0 --port $port
