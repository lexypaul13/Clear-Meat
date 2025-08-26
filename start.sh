#!/bin/bash
echo "🚀 Starting Clear-Meat API on Railway with Performance Optimizations... (v3)"
echo "PORT: $PORT"
echo "ENVIRONMENT: $ENVIRONMENT" 
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "Application files:"
ls -la app/

# Ensure PORT is set - Railway should provide this
if [ -z "$PORT" ]; then
    echo "WARNING: PORT not set by Railway, using default 8000"
    export PORT=8000
else
    echo "Using Railway PORT: $PORT"
fi

# Start the application with proper port handling
exec python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level info