"""Script to run database migrations."""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def run_migration(sql_file_path):
    """
    Run a SQL migration file against the database.
    
    Args:
        sql_file_path: Path to the SQL file
        
    Returns:
        bool: True if migration was successful, False otherwise
    """
    try:
        # Get database URL from environment
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logger.error("No DATABASE_URL found in environment variables")
            return False
            
        # Create SQLAlchemy engine
        engine = create_engine(database_url)
        
        # Read SQL file
        with open(sql_file_path, 'r') as f:
            sql = f.read()
            
        # Execute SQL
        with engine.connect() as conn:
            logger.info(f"Running migration: {sql_file_path}")
            conn.execute(text(sql))
            conn.commit()
            
        logger.info(f"Migration successful: {sql_file_path}")
        return True
    except Exception as e:
        logger.error(f"Error running migration {sql_file_path}: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python run_migration.py <sql_file_path>")
        sys.exit(1)
        
    sql_file_path = sys.argv[1]
    if not os.path.exists(sql_file_path):
        logger.error(f"SQL file not found: {sql_file_path}")
        sys.exit(1)
        
    success = run_migration(sql_file_path)
    sys.exit(0 if success else 1) 