#!/usr/bin/env python3

"""Simple test script for the MeatWise API."""

import json
import requests
import sys
import time

# API base URL
BASE_URL = "http://localhost:8000/api/v1"

# Test product code (barcode) - use one that's likely to exist in the database
TEST_BARCODE = "3760156840413"  # Example barcode for a product

def print_separator(title=None):
    """Print a separator line."""
    print("\n" + "=" * 80)
    if title:
        print(title)
        print("-" * 80)

def test_health_endpoint():
    """Test the API health endpoint."""
    print_separator("Testing API Health Endpoint")
    url = f"{BASE_URL}/health"
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

def test_products_list_endpoint():
    """Test the products list endpoint."""
    print_separator("Testing Products List Endpoint")
    url = f"{BASE_URL}/products"
    print(f"Testing URL: {url}")
    
    try:
        response = requests.get(url, timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Products found: {len(data)}")
                if data:
                    print("First product info:")
                    print(f"Name: {data[0].get('name', 'Unknown')}")
                    print(f"Code: {data[0].get('code', 'Unknown')}")
                    # Use the barcode from the first product for the next test
                    global TEST_BARCODE
                    TEST_BARCODE = data[0].get('code', TEST_BARCODE)
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

def test_product_endpoint():
    """Test the individual product endpoint."""
    print_separator("Testing Individual Product Endpoint")
    url = f"{BASE_URL}/products/{TEST_BARCODE}"
    print(f"Testing URL: {url}")
    
    try:
        response = requests.get(url, timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("Response data (summary):")
                product_info = data.get('product_info', {})
                print(f"Name: {product_info.get('name', 'Unknown')}")
                print(f"Brand: {product_info.get('brand', 'Unknown')}")
                
                risk_info = data.get('risk_info', {})
                print(f"Risk rating: {risk_info.get('risk_rating', 'Unknown')}")
                
                ingredients = data.get('ingredients', [])
                print(f"Ingredients count: {len(ingredients)}")
                
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
    print("Starting MeatWise API test...")
    print(f"Base URL: {BASE_URL}")
    
    # Run the tests
    success = 0
    total = 3
    
    # First test the health endpoint
    if test_health_endpoint():
        success += 1
    
    # Next test the products list
    if test_products_list_endpoint():
        success += 1
    
    # Finally test a specific product
    if test_product_endpoint():
        success += 1
    
    # Print summary
    print_separator("Test Summary")
    print(f"Tests passed: {success}/{total}")
    print(f"Tests failed: {total-success}/{total}")
    
    # Set exit code based on test success
    sys.exit(0 if success == total else 1) 