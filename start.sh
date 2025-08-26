#!/bin/bash
echo "🚀 Starting Clear-Meat API on Railway with Performance Optimizations... (v2)"
echo "PORT: $PORT"
echo "ENVIRONMENT: $ENVIRONMENT" 
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "Application files:"
ls -la app/

# Start the application
exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info