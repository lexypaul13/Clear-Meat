#!/usr/bin/env python
"""
Data Verification Script
-----------------------------
This script verifies the data in the database, showing insights on real vs mock data
and key statistics about the product database.

Dependencies:
- tabulate (install with: pip install tabulate)
"""

import os
import asyncio
import asyncpg
from dotenv import load_dotenv
from tabulate import tabulate

async def verify_data():
    """Verify and analyze data in the database"""
    # Load environment variables
    load_dotenv()
    
    # Connect to database
    print("Connecting to database...")
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    try:
        # Get overall counts
        product_count = await conn.fetchval("SELECT COUNT(*) FROM products")
        ingredient_count = await conn.fetchval("SELECT COUNT(*) FROM ingredients")
        relation_count = await conn.fetchval("SELECT COUNT(*) FROM product_ingredients")
        
        # Check for mock data
        mock_count = await conn.fetchval("""
        SELECT COUNT(*) FROM products WHERE code LIKE 'mock_%'
        """)
        
        # Real data count
        real_count = product_count - mock_count
        
        print("\n=== DATABASE OVERVIEW ===")
        print(f"Total products: {product_count}")
        print(f"- Products with real data: {real_count}")
        print(f"- Products with 'mock_' prefix: {mock_count}")
        print(f"Total ingredients: {ingredient_count}")
        print(f"Total product-ingredient relationships: {relation_count}")
        
        # Meat type distribution
        meat_distribution = await conn.fetch("""
        SELECT meat_type, COUNT(*) as count,
        ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM products))::numeric, 1) as percentage
        FROM products
        GROUP BY meat_type
        ORDER BY count DESC
        """)
        
        print("\n=== MEAT TYPE DISTRIBUTION ===")
        table_data = [(row['meat_type'], row['count'], f"{row['percentage']}%") for row in meat_distribution]
        print(tabulate(table_data, headers=["Meat Type", "Count", "Percentage"], tablefmt="simple"))
        
        # Risk rating distribution
        risk_distribution = await conn.fetch("""
        SELECT risk_rating, COUNT(*) as count,
        ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM products))::numeric, 1) as percentage
        FROM products
        GROUP BY risk_rating
        ORDER BY count DESC
        """)
        
        print("\n=== RISK RATING DISTRIBUTION ===")
        table_data = [(row['risk_rating'], row['count'], f"{row['percentage']}%") for row in risk_distribution]
        print(tabulate(table_data, headers=["Risk Rating", "Count", "Percentage"], tablefmt="simple"))
        
        # Top ingredients
        top_ingredients = await conn.fetch("""
        SELECT i.name, COUNT(pi.product_code) as product_count
        FROM ingredients i
        JOIN product_ingredients pi ON i.id = pi.ingredient_id
        GROUP BY i.name
        ORDER BY product_count DESC
        LIMIT 10
        """)
        
        print("\n=== TOP 10 INGREDIENTS ===")
        table_data = [(row['name'], row['product_count']) for row in top_ingredients]
        print(tabulate(table_data, headers=["Ingredient", "Product Count"], tablefmt="simple"))
        
        # Products with most ingredients
        products_with_most_ingredients = await conn.fetch("""
        SELECT p.name, p.code, COUNT(pi.ingredient_id) as ingredient_count
        FROM products p
        JOIN product_ingredients pi ON p.code = pi.product_code
        GROUP BY p.name, p.code
        ORDER BY ingredient_count DESC
        LIMIT 5
        """)
        
        print("\n=== PRODUCTS WITH MOST INGREDIENTS ===")
        table_data = [(row['name'], row['code'], row['ingredient_count']) for row in products_with_most_ingredients]
        print(tabulate(table_data, headers=["Product", "Code", "Ingredient Count"], tablefmt="simple"))
        
    except Exception as e:
        print(f"Error verifying data: {str(e)}")
    finally:
        await conn.close()
        print("\nDatabase connection closed")

if __name__ == "__main__":
    asyncio.run(verify_data()) 