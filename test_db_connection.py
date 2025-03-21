"""
Test script to verify connection to Supabase PostgreSQL database.
"""
import sys
from sqlalchemy import text

sys.path.append(".")  # Add the current directory to the path

from app.db.session import engine

def test_connection():
    """Test the connection to the PostgreSQL database."""
    try:
        # Try to execute a simple query
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Successfully connected to the PostgreSQL database!")
            
            # Try to query the ingredients table
            result = connection.execute(text("SELECT COUNT(*) FROM ingredients"))
            count = result.scalar()
            print(f"✅ Found {count} ingredients in the database")
            
    except Exception as e:
        print("❌ Failed to connect to the database:")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_connection() 