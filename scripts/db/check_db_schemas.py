"""Diagnostic script to check database schemas and models."""

import os
import sys
from sqlalchemy import create_engine, inspect, MetaData, Table
import uuid

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.db.models import Base, User, Product, ScanHistory, UserFavorite
from app.models.user import UserFavorite as PydanticUserFavorite


def check_db_schemas():
    """Check database schemas and model compatibility."""
    # Create engine
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        echo=True,
    )
    
    # Connect to database
    print(f"Connecting to database: {settings.DATABASE_URL.replace(settings.POSTGRES_PASSWORD, '****')}")
    
    with engine.connect() as conn:
        # Get inspector
        inspector = inspect(engine)
        
        # Get table names
        tables = inspector.get_table_names()
        print(f"Tables in database: {tables}")
        
        # Check user_favorites table
        if "user_favorites" in tables:
            columns = inspector.get_columns("user_favorites")
            print(f"Columns in user_favorites table:")
            for col in columns:
                print(f"  {col['name']}: {col['type']}")
        
        # Compare with SQLAlchemy model
        print("\nSQLAlchemy UserFavorite model:")
        for column in UserFavorite.__table__.columns:
            print(f"  {column.name}: {column.type}")
        
        # Compare with Pydantic model
        print("\nPydantic UserFavorite model:")
        for field_name, field in PydanticUserFavorite.model_fields.items():
            print(f"  {field_name}: {field.annotation}")
    
    print("\nDiagnostic complete.")


if __name__ == "__main__":
    check_db_schemas() 