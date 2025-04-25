#!/usr/bin/env python
import os
import asyncio
import asyncpg
from dotenv import load_dotenv
import logging
from tabulate import tabulate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def check_db_stats():
    # Connect to the database
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    try:
        # Get products without images
        no_images = await conn.fetch("""
            SELECT 
                meat_type,
                risk_rating,
                COUNT(*) as count,
                ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM products WHERE image_data IS NULL))::numeric, 1) as percentage
            FROM products 
            WHERE image_data IS NULL
            GROUP BY meat_type, risk_rating
            ORDER BY count DESC
        """)
        
        print("\nProducts Without Images (6,264 total):")
        print("------------------------------------")
        table_data = [(row['meat_type'], row['risk_rating'], row['count'], f"{row['percentage']}%") for row in no_images]
        print(tabulate(table_data, headers=["Meat Type", "Risk Rating", "Count", "Percentage"], tablefmt="grid"))
        
        # Get last update times for products without images using a subquery
        last_updates = await conn.fetch("""
            WITH update_categories AS (
                SELECT 
                    CASE 
                        WHEN last_updated IS NULL THEN 'Never Updated'
                        WHEN last_updated < NOW() - INTERVAL '7 days' THEN 'Over 7 days ago'
                        WHEN last_updated < NOW() - INTERVAL '3 days' THEN '3-7 days ago'
                        WHEN last_updated < NOW() - INTERVAL '1 day' THEN '1-3 days ago'
                        ELSE 'Last 24 hours'
                    END as update_time
                FROM products 
                WHERE image_data IS NULL
            )
            SELECT 
                update_time,
                COUNT(*) as count,
                ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM products WHERE image_data IS NULL))::numeric, 1) as percentage
            FROM update_categories
            GROUP BY update_time
            ORDER BY 
                CASE update_time
                    WHEN 'Never Updated' THEN 1
                    WHEN 'Over 7 days ago' THEN 2
                    WHEN '3-7 days ago' THEN 3
                    WHEN '1-3 days ago' THEN 4
                    WHEN 'Last 24 hours' THEN 5
                END
        """)
        
        print("\nLast Update Times for Products Without Images:")
        print("-------------------------------------------")
        table_data = [(row['update_time'], row['count'], f"{row['percentage']}%") for row in last_updates]
        print(tabulate(table_data, headers=["Last Update", "Count", "Percentage"], tablefmt="grid"))
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_db_stats()) 