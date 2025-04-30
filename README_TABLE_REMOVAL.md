# Table Removal Process for MeatWise API

This document provides instructions for removing unused and backup tables from the MeatWise API database.

## Background

Several tables in the database are no longer needed and have been identified for removal:

- `ingredients_backup_20240430`: Backup table from April 30, 2024
- `price_history`: Historical pricing data (now redundant)
- `product_alternatives`: Alternative product recommendations (feature deprecated)
- `product_errors`: Error logs (no longer used)
- `product_ingredients_backup_20240430`: Backup table from April 30, 2024
- `product_nutrition`: Detailed nutrition data (now consolidated into products table)
- `supply_chain`: Supply chain data (feature deprecated)

## Prerequisites

1. Make sure you have the following environment variables set:
   - `DATABASE_URL`: Connection string for your Supabase PostgreSQL database
   - Or individual connection parameters:
     - `DB_HOST`: Database host
     - `DB_PORT`: Database port (default: 5432)
     - `DB_NAME`: Database name (default: postgres)
     - `DB_USER`: Database username (default: postgres)
     - `DB_PASSWORD`: Database password

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Execution Process

### Step 1: Run the Table Removal Script

```bash
python scripts/remove_backup_tables.py
```

This script performs the following actions:
1. Checks which tables exist in the database
2. Executes the migration SQL in a transaction
3. Verifies all tables were successfully removed
4. Logs the entire process to `table_removal.log`

### Step 2: Verify Application Functionality

After removing the tables, verify that your application still functions correctly:

```bash
# Start the API
uvicorn app.main:app --reload --port 8001
```

Test the following API endpoints:
- `GET /api/v1/products`: Should work normally
- `GET /api/v1/products/{code}`: Should work normally
- `GET /api/v1/products/{code}/alternatives`: Should return an empty list

### Step 3: Review Logs

Check the generated logs to ensure everything went smoothly:

```bash
cat table_removal.log
```

## Common Issues and Troubleshooting

### Database Connection Issues

If you encounter connection errors:
1. Verify your `DATABASE_URL` or individual connection parameters
2. Check if your Supabase instance is running
3. Ensure you have the necessary permissions

### Table Dependencies

If tables cannot be dropped due to dependencies:
1. The script will automatically attempt to remove foreign key constraints
2. Check the logs for specific constraint errors
3. If needed, manually remove dependant objects first

### Application Errors

If the application shows errors after table removal:
1. Check the logs for references to missing tables
2. Ensure all code that referenced these tables has been updated
3. Restart the application after making any code changes

## Technical Details

### Migration SQL

The SQL migration file is located at `migrations/20240515_remove_backup_tables.sql`. It contains:
- Table existence checks
- Foreign key constraint removal
- Table drop commands in proper dependency order
- Verification steps

### Placeholder Models

To maintain backward compatibility, placeholder SQLAlchemy model classes have been added to `app/db/models.py`. These models:
- Have the same structure as the original tables
- Point to non-existent tables (with clear documentation)
- Allow code to reference these models without errors

### API Endpoint Updates

The following endpoint was updated to handle missing tables:
- `GET /api/v1/products/{code}/alternatives`: Returns an empty list with appropriate logging

## Schema Documentation

A detailed description of the schema changes is available in:
`docs/schema_changes/20240515_removed_tables.md` 