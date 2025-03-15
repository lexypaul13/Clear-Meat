from app.database.db_setup import setup_database

if __name__ == "__main__":
    # For local development, use SQLite
    DATABASE_URL = "sqlite:///./meat_products.db"
    # In production, use PostgreSQL
    # DATABASE_URL = "postgresql://username:password@host:5432/meatproducts"
    setup_database(DATABASE_URL) 