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
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
    """Read SQL content from file."""
    try:
        logger.info("Reading SQL file")
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error("Error reading SQL file")
        raise

def execute_sqls_using_dashboard(sql_content: str) -> None:
    """Print SQL instructions for manual execution in Supabase Dashboard."""
    print("\n" + "="*80)
    print("PLEASE EXECUTE THE FOLLOWING SQL IN THE SUPABASE DASHBOARD SQL EDITOR:")
    print("="*80 + "\n")
    print(sql_content)
    print("\n" + "="*80)
    logger.info("Please copy and run the SQL commands in the Supabase Dashboard SQL Editor.")

def main():
    """Main function to run the migration."""
    try:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Construct the path to the SQL file
        file_path = os.path.join(script_dir, '..', 'supabase', 'migrations', '20240320000000_weighted_scoring.sql')
        
        # Read the SQL content
        sql_content = read_sql_file(file_path)
        
        # Print instructions
        print("\n" + "="*80)
        print("PLEASE EXECUTE THE FOLLOWING SQL IN THE SUPABASE DASHBOARD SQL EDITOR:")
        print("="*80 + "\n")
        print(sql_content)
        print("\n" + "="*80)
        logger.info("Please copy and run the SQL commands in the Supabase Dashboard SQL Editor.")
        
    except FileNotFoundError:
        logger.error("Migration file not found")
        sys.exit(1)
    except Exception as e:
        logger.error("Error running migration")
        sys.exit(1)
    finally:
        logger.info("Migration script completed - please run the SQL in Supabase Dashboard")

if __name__ == "__main__":
    main() 