#!/bin/bash
# This script starts the MeatWise API, loading configuration from .env.local

# Activate virtual environment if not already activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Load environment variables from .env.local
if [[ -f .env.local ]]; then
    echo "Loading local environment variables from .env.local..."
    set -a # Automatically export all variables
    source .env.local
    set +a # Stop automatically exporting
else
    echo "Warning: .env.local file not found. Using default or system environment variables."
fi

# --- Removed explicit unsetting and setting --- 
# echo "Unsetting existing environment variables..."
# unset DATABASE_URL
# unset SUPABASE_URL
# unset SUPABASE_KEY
# unset SUPABASE_SERVICE_KEY
# unset BACKEND_CORS_ORIGINS
# unset GEMINI_API_KEY

# --- Removed explicit setting of URLs/Keys - now relying on .env.local --- 
# # If remote/testing/specific data is needed, use these Supabase settings
# export SUPABASE_URL="https://szswmlkhirkmozwvhpnc.supabase.co"
# export SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN6c3dtbGtoaXJrbW96d3ZocG5jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyNjY5NTIsImV4cCI6MjA1Nzg0Mjk1Mn0.yc4eC9f7IAjdNlav0GfxfkaeJAKZp-w1hPGHB0lMqPs"
# 
# # Set the correct local DATABASE_URL for SQLAlchemy
# export DATABASE_URL="postgresql://postgres:postgres@localhost:54322/postgres"

# Set DEBUG mode for detailed logging (can be overridden by .env.local)
export DEBUG="${DEBUG:-true}" # Default to true if not set in .env.local

# Verify the environment is correctly set
echo "===== Environment Check (Loaded from .env.local / System) ====="
echo "DATABASE_URL: ${DATABASE_URL:-Not Set}"
echo "SUPABASE_URL: ${SUPABASE_URL:-Not Set}"
echo "SUPABASE_KEY: ${SUPABASE_KEY:0:10}..." # Only show first 10 chars for security
echo "SUPABASE_SERVICE_KEY: ${SUPABASE_SERVICE_KEY:0:10}..."
echo "DEBUG: ${DEBUG}"

# Perform Supabase connectivity test (if URL and Key are set)
if [[ -n "$SUPABASE_URL" && -n "$SUPABASE_KEY" ]]; then
    echo "===== Checking Supabase Connectivity ====="
    if command -v curl &> /dev/null; then
        echo "Testing connection to Supabase..."
        RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -H "apikey: $SUPABASE_KEY" "$SUPABASE_URL/rest/v1/")
        if [ "$RESPONSE" -eq 200 ] || [ "$RESPONSE" -eq 401 ] || [ "$RESPONSE" -eq 404 ]; then
            echo "Supabase connection test: SUCCESS (HTTP $RESPONSE)"
        else
            echo "Supabase connection test: FAILED (HTTP $RESPONSE)"
            echo "Continuing anyway, but expect potential connectivity issues"
        fi
    else
        echo "curl not found, skipping connection test"
    fi
else
    echo "Skipping Supabase connection test: URL or Key not set."
fi

# Start the server on port 8001
echo "Starting server (config from .env.local / system)..."
uvicorn app.main:app --port 8001 --host 0.0.0.0 --workers 1

# Note: This script exits when uvicorn exits 