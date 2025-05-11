# MeatWise Database Migration Guide

This guide explains how to use both local PostgreSQL and Supabase databases with the MeatWise API.

## Overview

The MeatWise API has been updated to support both:
- **Local PostgreSQL database** - For fast, offline development
- **Supabase database** - For production deployment

This allows you to develop quickly with a local database and then deploy to production without code changes.

## Files Added or Modified

1. **New Files**:
   - `app/db/connection.py` - New database connection module supporting both environments
   - `scripts/switch_env.py` - Script to switch between environments
   - `start_app.py` - Starter script that handles environment switching and server startup

2. **Modified Files**:
   - `app/api/v1/endpoints/products.py` - Updated to use the new connection module
   - `app/main.py` - Updated to use the new connection module
   - `README.md` - Added documentation for environment switching

## How to Use

### 1. Setup Local Database

```bash
# Create local PostgreSQL database
createdb meatwise

# Create tables and import data
python create_tables.py
python import_products.py
```

### 2. Switch Between Environments

```bash
# Switch to local development
python scripts/switch_env.py local

# Switch to production
python scripts/switch_env.py production
```

### 3. Start the Application

```bash
# Easy way - uses the environment switcher automatically
./start_app.py --env local --reload

# Traditional way - after switching environment
uvicorn app.main:app --reload --port 8001
```

## Environment Configuration

Your `.env` file can store configurations for both environments:

```
# Active configuration (set by switch_env.py)
ENVIRONMENT=development
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/meatwise
SUPABASE_URL=http://localhost:54321
SUPABASE_KEY=your-local-key

# Production configuration (stored but not active until switched)
PRODUCTION_DATABASE_URL=your-production-db-url
PRODUCTION_SUPABASE_URL=your-production-supabase-url
PRODUCTION_SUPABASE_KEY=your-production-key
```

## Checking Environment

You can verify which environment is active by:

1. **API Health Check**:
   ```
   curl http://localhost:8001/health
   ```
   The response includes `"using_local_db": true/false`

2. **Application Logs**:
   The application logs will show:
   ```
   Using database connection: postgresql://postgres:****@localhost:54322/meatwise
   Environment: development, Testing mode: false
   ```

## Benefits

1. **Faster Development**:
   - Local database queries are instant
   - No internet connection needed
   - No API rate limits

2. **Safe Deployment**:
   - Test locally before deploying
   - No risk of corrupting production data
   - Same code works in both environments

3. **Cost Savings**:
   - Reduce Supabase usage during development
   - No accidental charges from testing
   - Better resource management 