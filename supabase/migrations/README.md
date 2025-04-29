# Database Migrations

This directory contains migration scripts for the Supabase PostgreSQL database.

## Running Migrations

To apply a migration script:

1. Log in to the Supabase dashboard at https://app.supabase.com
2. Select your project
3. Go to the SQL Editor
4. Create a new query
5. Copy and paste the contents of the migration file
6. Run the query

## Migration Files

- `20240316_initial_schema.sql`: Initial database schema
- `20240322_add_rls_policies.sql`: Added Row Level Security policies
- `20240322_fix_security_warnings.sql`: Fixed security warnings
- `20240424_remove_sodium.sql`: Removed sodium field
- `20240429_remove_unused_fields.sql`: Removed unused fields (source, ingredients_array, risk_score)

## Removed Fields

The latest migration (20240429) removes the following fields from the products table:

- `source`: This field was no longer needed as noted by the developer
- `ingredients_array`: This field wasn't used in the codebase
- `risk_score`: This field caused errors as it wasn't in the SQLAlchemy model

After running this migration, make sure any code that references these fields is updated. 