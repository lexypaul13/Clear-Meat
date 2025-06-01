#!/bin/bash

# Clear-Meat API Server Startup Script
# This script ensures proper environment variable loading

echo "🚀 Starting Clear-Meat API Server..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found!"
    echo "Please create a .env file with the required environment variables."
    echo "You can use .env.example as a template (if available)."
    echo ""
    echo "Required variables:"
    echo "  - SUPABASE_URL"
    echo "  - SUPABASE_KEY"
    echo "  - SUPABASE_SERVICE_KEY"
    echo "  - GEMINI_API_KEY"
    echo "  - SECRET_KEY"
    exit 1
fi

# Load environment variables
echo "📁 Loading environment variables from .env..."
set -a  # automatically export all variables
source .env
set +a  # stop automatically exporting

# Verify critical environment variables
echo "🔍 Verifying environment variables..."

MISSING_VARS=()

if [ -z "$SUPABASE_URL" ]; then
    MISSING_VARS+=("SUPABASE_URL")
fi

if [ -z "$SUPABASE_KEY" ]; then
    MISSING_VARS+=("SUPABASE_KEY")
fi

if [ -z "$SUPABASE_SERVICE_KEY" ]; then
    MISSING_VARS+=("SUPABASE_SERVICE_KEY")
fi

if [ -z "$GEMINI_API_KEY" ]; then
    MISSING_VARS+=("GEMINI_API_KEY")
fi

if [ -z "$SECRET_KEY" ]; then
    echo "⚠️  WARNING: SECRET_KEY not set. Using auto-generated key (insecure for production)."
fi

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ ERROR: Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please add these variables to your .env file."
    exit 1
fi

echo "✅ Environment variables loaded successfully!"

# Show configuration (without sensitive values)
echo ""
echo "📋 Configuration:"
echo "  SUPABASE_URL: $SUPABASE_URL"
echo "  SUPABASE_KEY: ****HIDDEN****"
echo "  SUPABASE_SERVICE_KEY: ****HIDDEN****"
echo "  GEMINI_API_KEY: ****HIDDEN****"
echo "  HOST: ${HOST:-0.0.0.0}"
echo "  PORT: ${PORT:-8000}"
echo ""

# Kill any existing server
echo "🔄 Checking for existing server..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true
sleep 2

# Start the server
echo "🚀 Starting server..."
echo "Server will be available at: http://localhost:${PORT:-8000}"
echo "API docs: http://localhost:${PORT:-8000}/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn app.main:app --reload --port ${PORT:-8000} --host ${HOST:-0.0.0.0} 