#!/bin/bash
echo "🚀 Starting Clear-Meat API on Railway..."
echo "PORT: $PORT"
echo "ENVIRONMENT: $ENVIRONMENT"
echo "Python version: $(python --version)"

# Start the application
python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info