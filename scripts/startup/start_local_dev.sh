#!/bin/bash
# This script starts the MeatWise API, loading configuration from .env with increased timeout

# Navigate to the project root directory
cd "$(dirname "$0")/../.."
PROJECT_ROOT="$(pwd)"
echo "Project root: $PROJECT_ROOT"

# Activate virtual environment if not already activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Activating virtual environment..."
    if [[ -f .venv/bin/activate ]]; then
        source .venv/bin/activate
    else
        echo "Virtual environment not found at $PROJECT_ROOT/.venv"
        echo "Please create a virtual environment first"
        exit 1
    fi
fi

# Clear any environment variables that might conflict
echo "Clearing any existing environment variables..."
unset SUPABASE_URL
unset SUPABASE_KEY
unset SUPABASE_SERVICE_KEY
unset DATABASE_URL

# Load environment variables from .env
if [[ -f .env ]]; then
    echo "Loading environment variables from .env..."
    # Export all variables in .env
    set -a
    source .env
    set +a
    
    # Ensure DATABASE_URL is explicitly exported
    if [[ -z "$DATABASE_URL" ]]; then
        echo "Warning: DATABASE_URL not found in .env, setting default"
        export DATABASE_URL="postgresql://postgres:postgres@localhost:54322/postgres"
    else
        echo "DATABASE_URL is set from .env"
    fi
else
    echo "ERROR: .env file not found. Please run scripts/startup/create_new_env.sh first."
    exit 1
fi

# Set DEBUG mode for detailed logging (can be overridden by .env)
export DEBUG="${DEBUG:-true}" # Default to true if not set in .env

# Set PostgreSQL statement timeout to a higher value (5 minutes)
export PGSTATEMENT_TIMEOUT="300000" # 5 minutes in milliseconds
echo "Setting PGSTATEMENT_TIMEOUT to ${PGSTATEMENT_TIMEOUT}ms"

# Verify the environment is correctly set
echo "===== Environment Check (Loaded from .env) ====="
echo "SUPABASE_URL: ${SUPABASE_URL:-Not Set}"
echo "SUPABASE_KEY: ${SUPABASE_KEY:0:10}..." # Only show first 10 chars for security
echo "DATABASE_URL: ${DATABASE_URL:-Not Set}"
echo "DEBUG: ${DEBUG}"
echo "PGSTATEMENT_TIMEOUT: ${PGSTATEMENT_TIMEOUT}ms"

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
            echo "Check your Supabase credentials and try again."
            echo "Continuing despite connection failure..."
        fi
    else
        echo "curl not found, skipping connection test"
    fi
else
    echo "WARNING: SUPABASE_URL or SUPABASE_KEY not set in .env"
    echo "Continuing without Supabase connection..."
fi

# Kill any existing process on port 8001
if command -v lsof &> /dev/null; then
    EXISTING_PID=$(lsof -ti:8001)
    if [ -n "$EXISTING_PID" ]; then
        echo "Killing existing process on port 8001 (PID: $EXISTING_PID)"
        kill -9 $EXISTING_PID
    fi
fi

# Enable test mode for development without strict database dependency
echo "Enabling test mode to bypass strict database checks..."
export TESTING=true

# Start the server on port 8001 with hot reload
echo "Starting server (config from .env)..."
export PYTHONUNBUFFERED=1  # Ensure Python output is not buffered
uvicorn app.main:app --port 8001 --host 0.0.0.0 --workers 1 --reload

# Note: This script exits when uvicorn exits 