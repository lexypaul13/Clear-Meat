#!/bin/bash
# This script starts the MeatWise API with the correct local database URL
# It explicitly unsets any existing DATABASE_URL and sets the correct one

# Activate virtual environment if not already activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Unset any existing DATABASE_URL (crucial step)
unset DATABASE_URL

# Unset any existing BACKEND_CORS_ORIGINS (crucial step)
unset BACKEND_CORS_ORIGINS

# Set the correct local DATABASE_URL
export DATABASE_URL="postgresql://postgres:postgres@localhost:54322/postgres"

# Verify the DATABASE_URL is correct
echo "Using DATABASE_URL: $DATABASE_URL"

# Start the server on port 8001 (without reload)
echo "Starting server..."
uvicorn app.main:app --port 8001

# Note: This script exits when uvicorn exits 