#!/usr/bin/env python3
"""
Simple test script for MeatWise API Product endpoints.
"""

import requests
import sys
from uuid import uuid4

# Configuration
BASE_URL = "http://127.0.0.1:8082/api/v1"
PRODUCTS_URL = f"{BASE_URL}/products/"

# Test data
test_product = {
    "code": f"test_{uuid4().hex[:8]}",
    "name": "Test Beef Jerky",
    "brand": "TestMeat",
    "description": "A test product",
    "ingredients_text": "Beef, salt, spices",
    "calories": 150.0,
    "protein": 25.0,
    "fat": 5.0,
    "carbohydrates": 3.0,
    "salt": 1.2,
    "meat_type": "beef",
    "contains_nitrites": True,
    "contains_phosphates": False,
    "contains_preservatives": True,
    "antibiotic_free": False,
    "hormone_free": False,
    "pasture_raised": False,
    "risk_rating": "Red",
    "risk_score": 70,
    "image_url": "https://example.com/image.jpg",
    "source": "test"
}

print("🧪 Testing Product API endpoints 🧪")

# Test 1: List all products
print("\n1. Testing GET /products")
response = requests.get(PRODUCTS_URL)
if response.status_code == 200:
    products = response.json()
    print(f"✅ Success: Retrieved {len(products)} products")
else:
    print(f"❌ Failed: Status code {response.status_code}")
    sys.exit(1)

# Test 2: Create a new product
print("\n2. Testing POST /products")
response = requests.post(PRODUCTS_URL, json=test_product)
if response.status_code in (200, 201):
    created_product = response.json()
    product_code = created_product.get("code")
    print(f"✅ Success: Created product with code {product_code}")
else:
    print(f"❌ Failed: Status code {response.status_code}")
    print(f"Response: {response.text}")
    sys.exit(1)

# Test 3: Get the created product
print(f"\n3. Testing GET /products/{product_code}")
response = requests.get(f"{PRODUCTS_URL}{product_code}")
if response.status_code == 200:
    product = response.json()
    print(f"✅ Success: Retrieved product {product.get('product', {}).get('name')}")
else:
    print(f"❌ Failed: Status code {response.status_code}")
    print(f"Response: {response.text}")

# Test 4: Get product alternatives
print(f"\n4. Testing GET /products/{product_code}/alternatives")
response = requests.get(f"{PRODUCTS_URL}{product_code}/alternatives")
if response.status_code == 200:
    alternatives = response.json()
    print(f"✅ Success: Retrieved {len(alternatives)} product alternatives")
else:
    print(f"❌ Failed: Status code {response.status_code}")
    print(f"Response: {response.text}")

print("\n✅ All tests completed!") 