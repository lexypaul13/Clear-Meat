#!/bin/bash
# This script starts the MeatWise API with the correct local database URL
# It explicitly unsets any existing environment variables and sets the correct ones

# Activate virtual environment if not already activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Unset any existing environment variables (crucial step)
echo "Unsetting existing environment variables..."
unset DATABASE_URL
unset SUPABASE_URL
unset SUPABASE_KEY
unset SUPABASE_SERVICE_KEY
unset BACKEND_CORS_ORIGINS
unset GEMINI_API_KEY

# If remote/testing/specific data is needed, use these Supabase settings
export SUPABASE_URL="https://szswmlkhirkmozwvhpnc.supabase.co"
export SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN6c3dtbGtoaXJrbW96d3ZocG5jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyNjY5NTIsImV4cCI6MjA1Nzg0Mjk1Mn0.yc4eC9f7IAjdNlav0GfxfkaeJAKZp-w1hPGHB0lMqPs"

# Set the correct local DATABASE_URL for SQLAlchemy
export DATABASE_URL="postgresql://postgres:postgres@localhost:54322/postgres"

# Set DEBUG mode for detailed logging
export DEBUG="true"

# Verify the environment is correctly set
echo "===== Environment Check ====="
echo "DATABASE_URL: $DATABASE_URL"
echo "SUPABASE_URL: $SUPABASE_URL"
echo "SUPABASE_KEY: ${SUPABASE_KEY:0:10}..." # Only show first 10 chars for security

# Perform Supabase connectivity test
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

# Start the server on port 8001
echo "Starting server with DEBUG logging enabled (no reload)..."
uvicorn app.main:app --port 8001 --host 0.0.0.0 --workers 1

# Note: This script exits when uvicorn exits 