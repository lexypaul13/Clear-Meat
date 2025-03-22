#!/usr/bin/env python3
"""
Simple test script for MeatWise API Ingredient endpoints.
"""

import requests
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8082/api/v1"
INGREDIENTS_URL = f"{BASE_URL}/ingredients/"

print("🧪 Testing Ingredient API endpoints 🧪")

# Test 1: List all ingredients
print("\n1. Testing GET /ingredients")
response = requests.get(INGREDIENTS_URL)
if response.status_code == 200:
    ingredients = response.json()
    print(f"✅ Success: Retrieved {len(ingredients)} ingredients")
    
    # If we have any ingredients, test getting details for the first one
    if ingredients:
        ingredient_id = ingredients[0].get("id")
        
        # Test 2: Get specific ingredient details
        print(f"\n2. Testing GET /ingredients/{ingredient_id}")
        response = requests.get(f"{INGREDIENTS_URL}{ingredient_id}")
        if response.status_code == 200:
            ingredient = response.json()
            print(f"✅ Success: Retrieved ingredient '{ingredient.get('name')}'")
        else:
            print(f"❌ Failed: Status code {response.status_code}")
            print(f"Response: {response.text}")
    else:
        print("\nNo ingredients found to test details endpoint")
else:
    print(f"❌ Failed: Status code {response.status_code}")
    sys.exit(1)

print("\n✅ All tests completed!") 