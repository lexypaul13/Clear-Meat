#!/usr/bin/env python
"""
Database Image Statistics
------------------------
This script analyzes the meat products in the database and provides statistics about image availability.
"""

import os
import logging
import asyncio
from dotenv import load_dotenv
from tabulate import tabulate
import asyncpg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def check_image_stats():
    """Analyze image statistics in the database"""
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    try:
        # Get comprehensive image statistics
        stats = await conn.fetch("""
            WITH stats AS (
                SELECT
                    COUNT(*) as total_products,
                    COUNT(CASE WHEN image_data IS NOT NULL THEN 1 END) as with_image_data,
                    COUNT(CASE WHEN image_data IS NULL THEN 1 END) as without_image_data,
                    COUNT(CASE WHEN image_url IS NOT NULL AND image_url != '' THEN 1 END) as with_url,
                    COUNT(CASE WHEN image_url IS NULL OR image_url = '' THEN 1 END) as without_url,
                    COUNT(CASE WHEN octet_length(image_data) > 0 THEN 1 END) as non_empty_images,
                    COUNT(CASE WHEN octet_length(image_data) = 0 THEN 1 END) as empty_images,
                    AVG(CASE WHEN image_data IS NOT NULL THEN octet_length(image_data) END) as avg_image_size,
                    MIN(CASE WHEN image_data IS NOT NULL THEN octet_length(image_data) END) as min_image_size,
                    MAX(CASE WHEN image_data IS NOT NULL THEN octet_length(image_data) END) as max_image_size
                FROM products
            )
            SELECT 
                *,
                ROUND((with_image_data::numeric / total_products * 100)::numeric, 1) as with_image_percent,
                ROUND((without_image_data::numeric / total_products * 100)::numeric, 1) as without_image_percent
            FROM stats
        """)
        
        base_stats = stats[0]
        print("\nDatabase Image Statistics:")
        print("------------------------")
        table_data = [
            ["Total Products", base_stats['total_products']],
            ["Products with Image Data", f"{base_stats['with_image_data']} ({base_stats['with_image_percent']}%)"],
            ["Products without Image Data", f"{base_stats['without_image_data']} ({base_stats['without_image_percent']}%)"],
            ["Products with Image URLs", base_stats['with_url']],
            ["Products without Image URLs", base_stats['without_url']],
            ["Non-empty Images", base_stats['non_empty_images']],
            ["Empty Images", base_stats['empty_images']],
            ["Average Image Size", f"{int(base_stats['avg_image_size'] or 0):,} bytes"],
            ["Minimum Image Size", f"{base_stats['min_image_size'] or 0:,} bytes"],
            ["Maximum Image Size", f"{base_stats['max_image_size'] or 0:,} bytes"]
        ]
        print(tabulate(table_data, headers=["Metric", "Value"], tablefmt="grid"))

        # Get distribution by meat type
        meat_stats = await conn.fetch("""
            SELECT 
                meat_type,
                COUNT(*) as total,
                COUNT(CASE WHEN image_data IS NOT NULL THEN 1 END) as with_images,
                COUNT(CASE WHEN image_data IS NULL THEN 1 END) as without_images,
                ROUND((COUNT(CASE WHEN image_data IS NOT NULL THEN 1 END)::numeric / COUNT(*)::numeric * 100)::numeric, 1) as success_rate
            FROM products
            GROUP BY meat_type
            ORDER BY total DESC
        """)
        
        print("\nImage Statistics by Meat Type:")
        print("----------------------------")
        table_data = [(
            row['meat_type'] or 'Unknown',
            row['total'],
            row['with_images'],
            row['without_images'],
            f"{row['success_rate']}%"
        ) for row in meat_stats]
        print(tabulate(table_data, 
                      headers=["Meat Type", "Total", "With Images", "Without Images", "Success Rate"],
                      tablefmt="grid"))

        # Get recent scraping activity
        recent_activity = await conn.fetch("""
            SELECT 
                date_trunc('hour', last_updated) as hour,
                COUNT(*) as attempts,
                COUNT(CASE WHEN image_data IS NOT NULL THEN 1 END) as successes,
                ROUND((COUNT(CASE WHEN image_data IS NOT NULL THEN 1 END)::numeric / COUNT(*)::numeric * 100)::numeric, 1) as success_rate
            FROM products
            WHERE last_updated >= NOW() - INTERVAL '24 hours'
            GROUP BY hour
            ORDER BY hour DESC
        """)
        
        if recent_activity:
            print("\nRecent Scraping Activity (Last 24 Hours):")
            print("---------------------------------------")
            table_data = [(
                row['hour'].strftime('%Y-%m-%d %H:00'),
                row['attempts'],
                row['successes'],
                f"{row['success_rate']}%"
            ) for row in recent_activity]
            print(tabulate(table_data, 
                          headers=["Hour", "Attempts", "Successes", "Success Rate"],
                          tablefmt="grid"))
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_image_stats()) 