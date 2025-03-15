from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

from app.database.database import Base
from app.services.product_service import fetch_meat_products

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # For local development, use SQLite
    DATABASE_URL = "sqlite:///./meat_products.db"
    # In production, use PostgreSQL
    # DATABASE_URL = "postgresql://username:password@host:5432/meatproducts"
    
    # For SQLite, we need to add connect_args
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Create a database session
    db = SessionLocal()
    try:
        # Fetch products
        fetch_meat_products(db)
    finally:
        db.close()

if __name__ == "__main__":
    main() 