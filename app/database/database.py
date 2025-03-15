from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# For local development, use SQLite
DATABASE_URL = "sqlite:///./meat_products.db"
# In production, use PostgreSQL
# DATABASE_URL = "postgresql://username:password@host:5432/meatproducts"
# DATABASE_URL = os.environ.get("DATABASE_URL")

# For SQLite, we need to add connect_args
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 