#!/usr/bin/env python3
"""
Live Test Script for MeatWise API Product and Ingredient Endpoints.
This script tests all the CRUD operations for products and ingredients.
"""

import requests
import json
import sys
from uuid import uuid4
import time

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
PRODUCT_ENDPOINT = f"{BASE_URL}/products"
INGREDIENT_ENDPOINT = f"{BASE_URL}/ingredients"

# Sample data for testing
TEST_PRODUCT = {
    "code": f"test_{uuid4().hex[:8]}",
    "name": "Test Organic Chicken",
    "brand": "TestBrand",
    "description": "Organic chicken breast for testing",
    "ingredients_text": "Chicken, salt, herbs",
    "calories": 165.0,
    "protein": 31.0,
    "fat": 3.6,
    "carbohydrates": 0.0,
    "salt": 0.5,
    "meat_type": "chicken",
    "contains_nitrites": False,
    "contains_phosphates": False,
    "contains_preservatives": False,
    "antibiotic_free": True,
    "hormone_free": True,
    "pasture_raised": True,
    "risk_rating": "Green",
    "risk_score": 20,
    "image_url": "https://example.com/images/test-chicken.jpg",
    "source": "test_script"
}

TEST_INGREDIENT = {
    "name": f"Test Ingredient {uuid4().hex[:8]}",
    "description": "A test ingredient for API testing",
    "category": "preservative",
    "risk_level": "low",
    "concerns": ["Potential digestive issues in sensitive individuals"],
    "alternatives": ["Natural herbs", "Celery powder"]
}

def test_connection():
    """Test basic connection to the API."""
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print("✅ Connection to API successful")
            return True
        else:
            print(f"❌ Connection failed with status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection error. Is the API server running?")
        return False

def test_get_products():
    """Test GET /products endpoint."""
    print("\n1. Testing GET /products endpoint")
    try:
        response = requests.get(PRODUCT_ENDPOINT)
        if response.status_code == 200:
            products = response.json()
            print(f"✅ Successfully retrieved {len(products)} products")
            return True
        else:
            print(f"❌ Failed to retrieve products: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_create_product():
    """Test POST /products endpoint."""
    print("\n2. Testing POST /products endpoint")
    try:
        response = requests.post(PRODUCT_ENDPOINT, json=TEST_PRODUCT)
        if response.status_code in (200, 201):
            product = response.json()
            print(f"✅ Successfully created product: {product.get('name')} (code: {product.get('code')})")
            return product.get("code")
        else:
            print(f"❌ Failed to create product: {response.status_code}")
            if response.status_code == 422:
                print(f"Validation error: {response.json()}")
            return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def test_get_product(code):
    """Test GET /products/{code} endpoint."""
    print(f"\n3. Testing GET /products/{code} endpoint")
    try:
        response = requests.get(f"{PRODUCT_ENDPOINT}/{code}")
        if response.status_code == 200:
            product = response.json()
            print(f"✅ Successfully retrieved product: {product.get('product', {}).get('name')}")
            return True
        else:
            print(f"❌ Failed to retrieve product: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_update_product(code):
    """Test PUT /products/{code} endpoint."""
    print(f"\n4. Testing PUT /products/{code} endpoint")
    try:
        update_data = TEST_PRODUCT.copy()
        update_data["description"] = "Updated test description"
        update_data["risk_rating"] = "Yellow"
        
        response = requests.put(f"{PRODUCT_ENDPOINT}/{code}", json=update_data)
        if response.status_code == 200:
            product = response.json()
            print(f"✅ Successfully updated product: {product.get('name')}")
            return True
        else:
            print(f"❌ Failed to update product: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_delete_product(code):
    """Test DELETE /products/{code} endpoint."""
    print(f"\n5. Testing DELETE /products/{code} endpoint")
    try:
        response = requests.delete(f"{PRODUCT_ENDPOINT}/{code}")
        if response.status_code == 200:
            print(f"✅ Successfully deleted product")
            return True
        else:
            print(f"❌ Failed to delete product: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_get_ingredients():
    """Test GET /ingredients endpoint."""
    print("\n1. Testing GET /ingredients endpoint")
    try:
        response = requests.get(INGREDIENT_ENDPOINT)
        if response.status_code == 200:
            ingredients = response.json()
            print(f"✅ Successfully retrieved {len(ingredients)} ingredients")
            return True
        else:
            print(f"❌ Failed to retrieve ingredients: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_create_ingredient():
    """Test POST /ingredients endpoint."""
    print("\n2. Testing POST /ingredients endpoint")
    try:
        response = requests.post(INGREDIENT_ENDPOINT, json=TEST_INGREDIENT)
        if response.status_code in (200, 201):
            ingredient = response.json()
            print(f"✅ Successfully created ingredient: {ingredient.get('name')} (id: {ingredient.get('id')})")
            return ingredient.get("id")
        else:
            print(f"❌ Failed to create ingredient: {response.status_code}")
            if response.status_code == 422:
                print(f"Validation error: {response.json()}")
            return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def test_get_ingredient(ingredient_id):
    """Test GET /ingredients/{id} endpoint."""
    print(f"\n3. Testing GET /ingredients/{ingredient_id} endpoint")
    try:
        response = requests.get(f"{INGREDIENT_ENDPOINT}/{ingredient_id}")
        if response.status_code == 200:
            ingredient = response.json()
            print(f"✅ Successfully retrieved ingredient: {ingredient.get('name')}")
            return True
        else:
            print(f"❌ Failed to retrieve ingredient: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_update_ingredient(ingredient_id):
    """Test PUT /ingredients/{id} endpoint."""
    print(f"\n4. Testing PUT /ingredients/{ingredient_id} endpoint")
    try:
        update_data = TEST_INGREDIENT.copy()
        update_data["description"] = "Updated test description"
        update_data["risk_level"] = "medium"
        
        response = requests.put(f"{INGREDIENT_ENDPOINT}/{ingredient_id}", json=update_data)
        if response.status_code == 200:
            ingredient = response.json()
            print(f"✅ Successfully updated ingredient: {ingredient.get('name')}")
            return True
        else:
            print(f"❌ Failed to update ingredient: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_delete_ingredient(ingredient_id):
    """Test DELETE /ingredients/{id} endpoint."""
    print(f"\n5. Testing DELETE /ingredients/{ingredient_id} endpoint")
    try:
        response = requests.delete(f"{INGREDIENT_ENDPOINT}/{ingredient_id}")
        if response.status_code == 200:
            print(f"✅ Successfully deleted ingredient")
            return True
        else:
            print(f"❌ Failed to delete ingredient: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Main test function."""
    print("🧪 TESTING MEATWISE API ENDPOINTS 🧪")
    
    # Test connection to API
    if not test_connection():
        print("Exiting tests due to connection failure.")
        sys.exit(1)
    
    # Test product endpoints
    print("\n🔍 TESTING PRODUCT ENDPOINTS")
    if test_get_products():
        product_code = test_create_product()
        if product_code:
            test_get_product(product_code)
            test_update_product(product_code)
            test_delete_product(product_code)
    
    # Test ingredient endpoints
    print("\n🔍 TESTING INGREDIENT ENDPOINTS")
    if test_get_ingredients():
        ingredient_id = test_create_ingredient()
        if ingredient_id:
            test_get_ingredient(ingredient_id)
            test_update_ingredient(ingredient_id)
            test_delete_ingredient(ingredient_id)
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main() 