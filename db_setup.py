from sqlalchemy import create_engine
from main import Base
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_database(database_url):
    """
    Set up the database schema
    """
    try:
        logger.info(f"Connecting to database...")
        engine = create_engine(database_url)
        
        logger.info(f"Creating tables...")
        Base.metadata.create_all(bind=engine)
        
        logger.info(f"Database setup completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error setting up database: {str(e)}")
        return False

if __name__ == "__main__":
    # In production, use environment variables for database credentials
    DATABASE_URL = "postgresql://username:password@host:5432/meatproducts"
    setup_database(DATABASE_URL) 