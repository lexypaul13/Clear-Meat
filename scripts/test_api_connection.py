#!/usr/bin/env python
"""
Test OpenFoodFacts API Connectivity
----------------------------------
This script tests if we can connect to the OpenFoodFacts API and retrieve real product data.
"""

import asyncio
import aiohttp
import json
import sys

async def test_api_connectivity():
    """Test the connectivity to the OpenFoodFacts API"""
    print("Testing OpenFoodFacts API connectivity...")
    
    # Test product codes that should exist
    test_codes = [
        "3596710400737",  # Charal beef steak
        "3700841010013",  # Fleury Michon jambon
        "3228857000852",  # Herta diced bacon
    ]
    
    # Create session
    async with aiohttp.ClientSession() as session:
        for code in test_codes:
            print(f"\nTesting product code: {code}")
            try:
                # Make API request to get individual product
                url = f"https://world.openfoodfacts.org/api/v0/product/{code}.json"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('status') == 1:
                            product = data.get('product', {})
                            print(f"✅ SUCCESS! Found product: {product.get('product_name')}")
                            print(f"  Brand: {product.get('brands')}")
                            print(f"  Categories: {product.get('categories')}")
                            print(f"  Ingredients: {product.get('ingredients_text', '')[:100]}...")
                        else:
                            print(f"❌ API returned success but product not found: {data.get('status_verbose')}")
                    else:
                        print(f"❌ API request failed with status {response.status}")
                        response_text = await response.text()
                        print(f"  Response: {response_text[:200]}...")
            except Exception as e:
                print(f"❌ Error connecting to API: {str(e)}")
        
        # Now test search functionality 
        print("\nTesting search functionality...")
        try:
            # Make API request to search for products
            params = {
                'action': 'process',
                'json': 1,
                'page_size': 5,
                'page': 1,
                'tagtype_0': 'categories',
                'tag_contains_0': 'contains', 
                'tag_0': 'meat',
                'sort_by': 'popularity'
            }
            
            url = "https://world.openfoodfacts.org/cgi/search.pl"
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    products = data.get('products', [])
                    
                    if products:
                        print(f"✅ SUCCESS! Found {len(products)} products in search results")
                        print("\nSample products:")
                        for i, product in enumerate(products[:3]):
                            print(f"  {i+1}. {product.get('product_name')} (code: {product.get('code')})")
                    else:
                        print("❌ Search returned no products")
                else:
                    print(f"❌ Search API request failed with status {response.status}")
                    response_text = await response.text()
                    print(f"  Response: {response_text[:200]}...")
        except Exception as e:
            print(f"❌ Error with search API: {str(e)}")
    
    print("\nAPI connectivity test completed.")

if __name__ == "__main__":
    asyncio.run(test_api_connectivity()) 