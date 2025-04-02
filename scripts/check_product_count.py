#!/usr/bin/env python
"""
Check Product Count
------------------
Simple script to check how many products are in the database.
"""

import os
import asyncio
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def check_product_count():
    # Connect to the database
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    # Get total count
    total_count = await conn.fetchval("SELECT COUNT(*) FROM products")
    print(f"Total products in database: {total_count}")
    
    # Get count by meat type
    meat_types = await conn.fetch("""
        SELECT meat_type, COUNT(*) as count 
        FROM products 
        GROUP BY meat_type 
        ORDER BY count DESC
    """)
    
    print("\nBreakdown by meat type:")
    print("-----------------------")
    for row in meat_types:
        print(f"{row['meat_type']}: {row['count']}")
    
    # Get count by risk rating
    risk_ratings = await conn.fetch("""
        SELECT risk_rating, COUNT(*) as count 
        FROM products 
        GROUP BY risk_rating 
        ORDER BY count DESC
    """)
    
    print("\nBreakdown by risk rating:")
    print("-------------------------")
    for row in risk_ratings:
        print(f"{row['risk_rating']}: {row['count']}")
    
    # Close the connection
    await conn.close()

# Run the script
if __name__ == "__main__":
    asyncio.run(check_product_count()) 