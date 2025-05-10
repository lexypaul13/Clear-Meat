#!/bin/bash

# Make sure any existing .env is removed first
if [ -f .env ]; then
  echo "Removing existing .env file"
  rm .env
fi

# Ask for the Supabase key
echo "Enter your Supabase key (will not be shown):"
read -s SUPABASE_KEY
echo ""

# Create new .env file with remote Supabase settings
cat > .env << EOL
# Remote Supabase Settings
SUPABASE_URL=https://szswmlkhirkmozwvhpnc.supabase.co
SUPABASE_KEY=${SUPABASE_KEY}

# Database URL for SQLAlchemy
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres

# API Configuration
API_V1_STR=/api/v1

# CORS Configuration
BACKEND_CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501
EOL

# Make the file readable only by the owner
chmod 600 .env

echo ".env file created successfully with remote Supabase settings."
echo "The file is set to be readable only by you for security." 