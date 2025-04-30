#!/usr/bin/env python3
"""
Script to execute the weighted scoring migration SQL script.
This adds functions to support the rule-based weighted scoring system.
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

def execute_sqls_using_dashboard(sql_content: str) -> None:
    """Print SQL instructions for manual execution in Supabase Dashboard."""
    print("\n" + "="*80)
    print("PLEASE EXECUTE THE FOLLOWING SQL IN THE SUPABASE DASHBOARD SQL EDITOR:")
    print("="*80 + "\n")
    print(sql_content)
    print("\n" + "="*80)
    logger.info("Please copy and run the SQL commands in the Supabase Dashboard SQL Editor.")

def main():
    """Main function to parse arguments and execute migration."""
    parser = argparse.ArgumentParser(description="Execute weighted scoring migration")
    parser.add_argument(
        "--file", 
        default="../migrations/20240702_add_product_max_values_function.sql",
        help="Path to SQL migration file"
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
        
    # Read SQL content
    sql_content = read_sql_file(str(migration_path))
    
    # Print instructions for manual execution
    execute_sqls_using_dashboard(sql_content)
    
    logger.info("Migration script completed - please run the SQL in Supabase Dashboard")
    return 0

if __name__ == "__main__":
    exit(main()) 