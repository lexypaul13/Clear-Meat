#!/usr/bin/env python3
"""Script to create database tables."""

import os
import sys
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import List

# Set database URL directly - don't rely on environment variables
DATABASE_URL = "postgresql://postgres:postgres@localhost:54322/postgres"

# Create engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Import models - after engine/Base are defined
from app.db.models import Product, User, ScanHistory, UserFavorite

def create_tables():
    """Create all database tables."""
    print(f"Creating database tables using {DATABASE_URL}...")
    
    # Check existing tables
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print(f"Existing tables: {existing_tables}")
    
    # Create tables
    print("Creating tables from models...")
    Base.metadata.create_all(bind=engine)
    
    # Check tables again
    inspector = inspect(engine)
    new_tables = inspector.get_table_names()
    print(f"Tables after creation: {new_tables}")
    
    # Show which tables were created
    created_tables = set(new_tables) - set(existing_tables)
    if created_tables:
        print(f"Created tables: {created_tables}")
    else:
        print("No new tables were created. They might already exist.")
    
    print("Database tables operation completed!")

if __name__ == "__main__":
    create_tables() 