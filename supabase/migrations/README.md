# Managing Supabase Database Migrations

This directory contains sequential SQL migration scripts for the project's Supabase PostgreSQL database.
Proper migration management is crucial to keep your local development database (running in Docker) consistent with your deployed environments and prevent schema errors.

## Key Principles

*   **Single Source of Truth:** Migrations in this folder are the primary source of truth for the database schema.
*   **Never Modify Manually:** Do *not* manually alter your local or remote database schema (e.g., via Supabase Studio) without creating a corresponding migration file here.
*   **Test Locally First:** *Always* test migrations thoroughly in your local Docker environment *before* committing them.

## Local Development Workflow (Using Supabase CLI)

Follow these steps for making schema changes locally:

1.  **Create a New Migration File:**
    *   From the project root directory, run: `supabase migration new <your_change_description>`
    *   Example: `supabase migration new add_image_data_to_products`
    *   This creates a *new, uniquely timestamped* `.sql` file in this directory.

2.  **Edit the New Migration File:**
    *   Write the necessary SQL DDL statements (e.g., `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`).
    *   **Use `IF EXISTS` / `IF NOT EXISTS` clauses** for safety (e.g., `DROP TABLE IF EXISTS ...`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...`).
    *   Ensure your SQL is correct and handles dependencies (like foreign keys) if dropping objects.

3.  **Apply & Test Locally:**
    *   Ensure your local Supabase stack is running (`supabase status`). If not, start it (`supabase start`).
    *   Apply *only the latest* migration changes to your running local DB: `supabase migration up`
    *   **Alternatively, for a full reset (deletes local data):** Stop (`supabase stop`), optionally remove the DB volume (`docker volume rm supabase_db_meat-products-api`), and restart (`supabase start`). This forces *all* migrations to run from scratch.
    *   **Verify:** Check Supabase Studio (`http://localhost:54323`) to confirm the schema changes were applied correctly in the *local* database.
    *   **(Recommended):** Run your FastAPI application (`./start_local_dev.sh`) and test code that interacts with the changed schema.

4.  **Commit:**
    *   If local tests pass, commit the *new migration file* and any related application code changes (e.g., updated SQLAlchemy models) to Git.

## Syncing with Changes from Git

After pulling changes from Git that include new migration files:

1.  Ensure your local Supabase stack is running (`supabase status`, `supabase start`).
2.  Apply any new migrations pulled from the repository: `supabase migration up`
3.  Or, if significant changes occurred or you suspect drift, perform a full reset: `supabase stop && supabase start` (optionally removing the volume in between).

## Common Issues & Prevention (Lessons Learned)

*   **"Column does not exist" Errors:** Often caused by schema drift. Your local Docker DB schema doesn't match your code (e.g., SQLAlchemy models) or the remote DB. Fix by ensuring all schema changes are made via migrations and applied locally (`supabase migration up` or `supabase start` after a reset).
*   **"Duplicate Key" Migration Errors:** Caused by multiple migration files having the exact same timestamp prefix. Rename files to ensure unique timestamps (e.g., `YYYYMMDDHHMMSS_` or `YYYYMMDD01_`).
*   **Migration Script Errors ("relation does not exist"):** Occurs if a migration script tries to operate on a table/object that was already dropped by a *previous* migration. Ensure migrations are ordered correctly and use `IF EXISTS` clauses.

By consistently following the workflow above, you can minimize these types of problems.

## Migration Files

- `20240316_initial_schema.sql`: Initial database schema
- `