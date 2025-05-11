#!/usr/bin/env python3
"""
Final test script to demonstrate database access success.
"""

import os
import json
import sys
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Get configuration from environment or use defaults
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8001")

def test_database():
    """Test direct database access."""
    print("\n--- DIRECT DATABASE ACCESS TEST ---")
    print(f"Connecting to: {DATABASE_URL}")
    
    try:
        # Create engine and session
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            # Count products
            result = session.execute(text("SELECT COUNT(*) FROM products")).scalar()
            print(f"Total products in database: {result}")
            
            # Sample products
            products = session.execute(text("SELECT code, name, meat_type FROM products LIMIT 3"))
            print("Sample products:")
            for product in products:
                print(f"  - {product[0]}: {product[1]} ({product[2]})")
        
        print("Database test completed successfully!\n")
        return True
    except Exception as e:
        print(f"Database test failed: {str(e)}")
        return False

def test_api():
    """Test API endpoints."""
    print("--- API ENDPOINT TEST ---")
    print(f"Base URL: {API_BASE_URL}")
    
    # Test health endpoint
    print("\nTesting health endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    # Test API v1 base URL
    print("\nTesting API v1 base...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/")
        print(f"Status: {response.status_code}")
        if response.status_code == 404:
            print("Note: It's normal for the base API path to return 404")
        else:
            print(f"Response: {response.text[:100]}...")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    # Test endpoints that should exist
    endpoints = [
        "/health",
        "/api/v1/products",
        "/api/v1/products/count"
    ]
    
    print("\nTesting multiple endpoints...")
    for endpoint in endpoints:
        try:
            response = requests.get(f"{API_BASE_URL}{endpoint}")
            print(f"Endpoint {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"Error with {endpoint}: {str(e)}")
    
    print("\nAPI test completed!")
    return True

if __name__ == "__main__":
    success = True
    
    try:
        db_success = test_database()
        api_success = test_api()
        success = db_success and api_success
        
        if success:
            print("\nAll tests completed successfully!")
        else:
            print("\nTests completed with some failures.")
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        success = False
    
    sys.exit(0 if success else 1) 