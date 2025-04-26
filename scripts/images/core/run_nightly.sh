#!/bin/bash

# Set working directory to the project root
cd "$(dirname "$0")/../.."

# Set up logging
LOG_FILE="image_scraper.log"
echo "Starting nightly image scraping at $(date)" >> "$LOG_FILE"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run the script for 8 hours
python scripts/images/fix_images.py --batch-size 50 --max-retries 3 --time-limit 8

# Log completion
echo "Nightly image fixing completed at $(date)" >> "$LOG_FILE"

# Deactivate virtual environment if it was activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi 