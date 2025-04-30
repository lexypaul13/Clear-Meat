#!/usr/bin/env python
"""
Script to remove backup and unused tables from the MeatWise database
This script checks table existence before attempting removal and handles errors gracefully
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("table_removal.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("table_removal")

# Load environment variables
load_dotenv()

# Tables to be removed
TABLES_TO_REMOVE = [
    'ingredients_backup_20240430',
    'price_history',
    'product_alternatives',
    'product_errors',
    'product_ingredients_backup_20240430',
    'product_nutrition',
    'supply_chain'
]

def get_database_connection():
    """Establish connection to the database using environment variables"""
    try:
        # Use environment variables for connection details
        db_url = os.getenv("DATABASE_URL")
        
        if not db_url:
            # Construct from individual parts if DATABASE_URL is not set
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "postgres")
            db_user = os.getenv("DB_USER", "postgres")
            db_password = os.getenv("DB_PASSWORD", "postgres")
            
            db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        logger.info(f"Connecting to database...")
        conn = psycopg2.connect(db_url)
        logger.info(f"Connected successfully to the database")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to the database: {str(e)}")
        raise

def check_table_existence(conn, table_name):
    """Check if a table exists in the database"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                   SELECT FROM information_schema.tables 
                   WHERE table_schema = 'public' 
                   AND table_name = %s
                );
            """, (table_name,))
            exists = cursor.fetchone()[0]
            return exists
    except Exception as e:
        logger.error(f"Error checking if table {table_name} exists: {str(e)}")
        return False

def execute_migration_file(conn, migration_file_path):
    """Execute the SQL migration file"""
    try:
        logger.info(f"Executing migration from file: {migration_file_path}")
        
        # Read the migration file
        with open(migration_file_path, 'r') as f:
            migration_sql = f.read()
        
        # Execute the migration script
        with conn.cursor() as cursor:
            cursor.execute(migration_sql)
        
        conn.commit()
        logger.info("Migration executed successfully")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error executing migration: {str(e)}")
        return False

def verify_table_removal(conn):
    """Verify that all tables have been removed"""
    all_removed = True
    for table in TABLES_TO_REMOVE:
        exists = check_table_existence(conn, table)
        if exists:
            logger.warning(f"Table {table} still exists after migration!")
            all_removed = False
        else:
            logger.info(f"Verified: Table {table} has been successfully removed")
    
    return all_removed

def main():
    """Main function to execute the table removal process"""
    logger.info("Starting table removal process")
    
    conn = None
    try:
        # Get database connection
        conn = get_database_connection()
        
        # Check table existence before migration
        logger.info("Checking table existence before migration...")
        tables_exist = {}
        for table in TABLES_TO_REMOVE:
            tables_exist[table] = check_table_existence(conn, table)
            if tables_exist[table]:
                logger.info(f"Table {table} exists and will be removed")
            else:
                logger.info(f"Table {table} does not exist, will be skipped")
        
        # Check if any tables need to be removed
        if not any(tables_exist.values()):
            logger.info("None of the specified tables exist. No migration needed.")
            return
        
        # Path to migration file
        migration_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            'migrations', 
            '20240515_remove_backup_tables.sql'
        )
        
        # Execute migration
        success = execute_migration_file(conn, migration_file_path)
        
        if success:
            # Verify table removal
            all_removed = verify_table_removal(conn)
            
            if all_removed:
                logger.info("All tables have been successfully removed!")
            else:
                logger.warning("Some tables could not be removed. Check the logs for details.")
        else:
            logger.error("Migration failed. No tables were removed.")
    
    except Exception as e:
        logger.error(f"Unexpected error during table removal process: {str(e)}")
    
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")
    
    logger.info("Table removal process completed")

if __name__ == "__main__":
    main() 