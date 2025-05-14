#!/usr/bin/env python
"""
Product Retrieval Utility
This script provides functions to retrieve product information from the MeatWise database.
It consolidates functionality from multiple product retrieval scripts into a single utility.
"""

import os
import json
import sys
import requests
import logging
from typing import Dict, List, Optional, Union
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("product_retrieval")

# Load environment variables
load_dotenv()

def get_supabase_credentials() -> Dict[str, str]:
    """Get Supabase credentials from environment variables."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials in .env file")
    
    return {
        "url": supabase_url,
        "key": supabase_key
    }

def get_product(product_code: str) -> Dict:
    """
    Fetch a single product from Supabase by its code.
    
    Args:
        product_code: The product code to fetch
        
    Returns:
        Dict containing product information or error message
    """
    try:
        creds = get_supabase_credentials()
        
        # Build the API URL
        api_url = f"{creds['url']}/rest/v1/products"
        
        # Set headers for authentication
        headers = {
            "apikey": creds['key'],
            "Authorization": f"Bearer {creds['key']}",
            "Content-Type": "application/json"
        }
        
        # Set query parameters
        params = {
            "code": f"eq.{product_code}"
        }
        
        # Make the request
        response = requests.get(api_url, headers=headers, params=params)
        
        # Check if successful
        if response.status_code == 200:
            data = response.json()
            if data:
                return data[0]
            else:
                return {"error": f"Product with code {product_code} not found"}
        else:
            return {
                "error": f"Failed to fetch product: {response.status_code}",
                "message": response.text
            }
    except Exception as e:
        return {"error": f"Exception: {str(e)}"}

def get_products(
    limit: int = 10,
    skip: int = 0,
    meat_type: Optional[str] = None,
    risk_rating: Optional[str] = None,
    sort_by: str = "name"
) -> List[Dict]:
    """
    Fetch multiple products from the database with optional filtering.
    
    Args:
        limit: Maximum number of products to return
        skip: Number of products to skip (for pagination)
        meat_type: Filter products by meat type (beef, pork, chicken, etc.)
        risk_rating: Filter by risk rating (Red, Yellow, Green)
        sort_by: Field to sort results by
        
    Returns:
        List of product dictionaries
    """
    try:
        creds = get_supabase_credentials()
        
        # Build the API URL
        api_url = f"{creds['url']}/rest/v1/products"
        
        # Set headers for authentication
        headers = {
            "apikey": creds['key'],
            "Authorization": f"Bearer {creds['key']}",
            "Content-Type": "application/json"
        }
        
        # Build query parameters
        params = {
            "limit": limit,
            "offset": skip,
            "order": sort_by
        }
        
        # Add filters if provided
        if meat_type:
            params["meat_type"] = f"eq.{meat_type}"
        
        if risk_rating:
            params["risk_rating"] = f"eq.{risk_rating}"
        
        # Make the request
        logger.info(f"Fetching products with parameters: {params}")
        response = requests.get(api_url, headers=headers, params=params)
        
        # Check if successful
        if response.status_code == 200:
            products = response.json()
            logger.info(f"Found {len(products)} products")
            return products
        else:
            logger.error(f"Failed to fetch products: {response.status_code} - {response.text}")
            return {"error": f"API request failed with status code: {response.status_code}"}
    
    except Exception as e:
        logger.error(f"Error fetching products: {str(e)}")
        return {"error": str(e)}

def get_product_details(product_code: str) -> Dict:
    """
    Fetch detailed product information including alternatives.
    
    Args:
        product_code: The product code to fetch details for
        
    Returns:
        Dict containing detailed product information
    """
    try:
        creds = get_supabase_credentials()
        
        # Build the API URL
        api_url = f"{creds['url']}/rest/v1/products"
        
        # Set headers for authentication
        headers = {
            "apikey": creds['key'],
            "Authorization": f"Bearer {creds['key']}",
            "Content-Type": "application/json"
        }
        
        # Set query parameters
        params = {
            "code": f"eq.{product_code}",
            "select": "*"
        }
        
        # Make the request
        response = requests.get(api_url, headers=headers, params=params)
        
        # Check if successful
        if response.status_code == 200:
            data = response.json()
            if not data:
                logger.warning(f"Product with code {product_code} not found")
                return None
            
            product = data[0]
            
            # Get alternatives
            alternatives = get_product_alternatives(product_code, creds['url'], creds['key'])
            
            # Add alternatives to product data
            product['alternatives'] = alternatives
            
            return product
        else:
            logger.error(f"Failed to fetch product details: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error fetching product details: {str(e)}")
        return None

def get_product_alternatives(product_code: str, supabase_url: str, supabase_key: str) -> Dict:
    """
    Get alternatives for a product.
    
    NOTE: The product_alternatives table has been removed as of 2024-05-15.
    This function now returns an empty list with a log message.
    
    Args:
        product_code: The product code
        supabase_url: Supabase URL
        supabase_key: Supabase API key
        
    Returns:
        Dict: Empty list with a comment about table removal
    """
    logger.info(f"get_product_alternatives called for product {product_code}")
    logger.warning("product_alternatives table has been removed. Returning empty list.")
    
    return {
        "data": [],
        "count": 0,
        "note": "product_alternatives table has been removed (2024-05-15)"
    }

def print_product_summary(products: Union[List[Dict], Dict]) -> None:
    """
    Print a summary of the retrieved products.
    
    Args:
        products: List of product dictionaries or error dictionary
    """
    if isinstance(products, dict) and "error" in products:
        print(f"Error: {products['error']}")
        return
    
    print(f"\nFound {len(products)} products\n")
    print("-" * 50)
    
    for i, product in enumerate(products, 1):
        print(f"{i}. {product.get('name', 'Unknown')} ({product.get('brand', 'Unknown')})")
        print(f"   Code: {product.get('code', 'N/A')}")
        print(f"   Type: {product.get('meat_type', 'N/A')}")
        print(f"   Risk: {product.get('risk_rating', 'N/A')}")
        print("-" * 50)

def print_product_json(products: Union[List[Dict], Dict], indent: int = 2) -> None:
    """
    Print the full product data in JSON format.
    
    Args:
        products: List of product dictionaries or error dictionary
        indent: JSON indentation level
    """
    print(json.dumps(products, indent=indent))

if __name__ == "__main__":
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Product Retrieval Utility")
    parser.add_argument("--code", help="Product code to fetch")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of products to fetch")
    parser.add_argument("--skip", type=int, default=0, help="Number of products to skip")
    parser.add_argument("--meat-type", help="Filter by meat type (beef, pork, chicken, etc.)")
    parser.add_argument("--risk-rating", help="Filter by risk rating (Red, Yellow, Green)")
    parser.add_argument("--sort", default="name", help="Field to sort results by")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--details", action="store_true", help="Show detailed product information")
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.code:
        if args.details:
            product = get_product_details(args.code)
            if args.json:
                print_product_json(product)
            else:
                print_product_summary([product] if product else [])
        else:
            product = get_product(args.code)
            if args.json:
                print_product_json(product)
            else:
                print_product_summary([product] if isinstance(product, dict) and "error" not in product else [])
    else:
        products = get_products(
            limit=args.limit,
            skip=args.skip,
            meat_type=args.meat_type,
            risk_rating=args.risk_rating,
            sort_by=args.sort
        )
        
        if args.json:
            print_product_json(products)
        else:
            print_product_summary(products) 