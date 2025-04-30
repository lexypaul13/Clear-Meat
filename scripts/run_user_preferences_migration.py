#!/usr/bin/env python3
"""
Script to execute the user preferences migration SQL script.
This updates the database to support the new user onboarding screens.
"""

import os
import argparse
import logging
from pathlib import Path
from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """Initialize Supabase client from environment variables."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError(
            "Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_KEY environment variables."
        )
    
    return create_client(supabase_url, supabase_key)

def read_sql_file(file_path: str) -> str:
    """Read SQL file content."""
    logger.info(f"Reading SQL file: {file_path}")
    with open(file_path, "r") as f:
        return f.read()

def execute_migration(sql_content: str, execute_data_migration: bool = False) -> None:
    """Execute the SQL migration script."""
    try:
        supabase = get_supabase_client()
        
        # Split the SQL content by semicolons to execute each statement separately
        # This is a simple approach - more complex scripts might need a more sophisticated parser
        statements = sql_content.split(";")
        
        for statement in statements:
            # Skip empty statements
            if not statement.strip() or statement.strip().startswith("--"):
                continue
                
            # Skip the data migration function execution if not requested
            if "SELECT migrate_legacy_preferences()" in statement and not execute_data_migration:
                logger.info("Skipping data migration function execution (use --migrate-data to execute)")
                continue
                
            # Execute the statement
            logger.debug(f"Executing: {statement}")
            supabase.postgrest.rpc(
                "run_sql_statement",
                {"statement": statement}
            ).execute()
            
        logger.info("Migration executed successfully")
        
    except Exception as e:
        logger.error(f"Error executing migration: {str(e)}")
        raise

def main():
    """Main function to parse arguments and execute migration."""
    parser = argparse.ArgumentParser(description="Execute user preferences migration")
    parser.add_argument(
        "--file", 
        default="../migrations/20240701_update_user_preferences.sql",
        help="Path to SQL migration file"
    )
    parser.add_argument(
        "--migrate-data", 
        action="store_true",
        help="Execute the data migration function to convert legacy preferences"
    )
    args = parser.parse_args()
    
    # Resolve the file path
    script_dir = Path(__file__).parent.absolute()
    migration_path = Path(args.file)
    if not migration_path.is_absolute():
        migration_path = script_dir / migration_path
        
    if not migration_path.exists():
        logger.error(f"Migration file not found: {migration_path}")
        return 1
        
    # Read and execute the migration
    sql_content = read_sql_file(str(migration_path))
    
    if args.migrate_data:
        logger.info("Data migration requested - will convert legacy preferences to new format")
        
        # Add the migration function execution
        if "-- SELECT migrate_legacy_preferences()" in sql_content:
            sql_content = sql_content.replace(
                "-- SELECT migrate_legacy_preferences()", 
                "SELECT migrate_legacy_preferences()"
            )
    
    execute_migration(sql_content, args.migrate_data)
    logger.info("Migration completed")
    return 0

if __name__ == "__main__":
    exit(main()) 