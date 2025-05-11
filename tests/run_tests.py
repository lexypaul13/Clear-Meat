#!/usr/bin/env python3
"""
Test runner script for meat-products-api.
Runs database and API tests to verify the application is functioning correctly.
"""

import os
import sys
import importlib
import subprocess
from pathlib import Path

# Add the project root to the path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

def print_header(message):
    """Print a formatted header message."""
    print("\n" + "=" * 70)
    print(f" {message} ".center(70, "="))
    print("=" * 70 + "\n")

def run_db_tests():
    """Run database connection tests."""
    print_header("Database Tests")
    
    # Run the database connection test
    print("Running database connection test...")
    try:
        from tests.db.test_db import test_connection
        success = test_connection()
        if not success:
            print("Database connection test failed!")
            return False
    except Exception as e:
        print(f"Error running database tests: {str(e)}")
        return False
    
    return True

def run_api_tests():
    """Run API tests if the server is running."""
    print_header("API Tests")
    
    # Run the final test (comprehensive test)
    print("Running API connectivity test...")
    try:
        # Import the test module
        from tests.final_test import test_api
        test_api()
    except Exception as e:
        print(f"Error running API tests: {str(e)}")
        return False
    
    return True

def main():
    """Run all tests."""
    print_header("MeatWise API Tests")
    
    # Run database tests
    db_success = run_db_tests()
    
    # Run API tests
    api_success = run_api_tests()
    
    # Print summary
    print_header("Test Summary")
    print(f"Database tests: {'PASSED' if db_success else 'FAILED'}")
    print(f"API tests: {'PASSED' if api_success else 'FAILED'}")
    
    # Return exit code
    return 0 if db_success and api_success else 1

if __name__ == "__main__":
    sys.exit(main()) 