#!/usr/bin/env python3

"""Simple test script for the product API."""

import json
import requests
import sys

# API base URL
BASE_URL = "http://localhost:8000/api/v1/products"

# Test product code (barcode)
TEST_BARCODE = "1234567890123"

def print_separator(title=None):
    """Print a separator line."""
    print("\n" + "=" * 80)
    if title:
        print(title)
        print("-" * 80)

def test_product_endpoint():
    """Test the individual product endpoint."""
    print_separator("Testing Individual Product Endpoint")
    url = f"{BASE_URL}/{TEST_BARCODE}"
    print(f"Testing URL: {url}")
    
    try:
        response = requests.get(url, timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("Response data:")
                print(json.dumps(data, indent=2))
                return True
            except json.JSONDecodeError:
                print("Response is not valid JSON:")
                print(response.text)
                return False
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return False
    except requests.RequestException as e:
        print(f"Request error: {e}")
        return False

if __name__ == "__main__":
    test_product_endpoint() 