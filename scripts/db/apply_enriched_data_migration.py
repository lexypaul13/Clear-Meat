import os
import asyncio
import asyncpg
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def apply_migration():
    """Apply the migration to create enriched data tables"""
    load_dotenv()
    db_url = os.getenv('DATABASE_URL')
    
    try:
        # Connect to the database
        conn = await asyncpg.connect(db_url)
        
        # Read migration file
        with open('migrations/20240322_add_enriched_data_tables.sql', 'r') as f:
            migration_sql = f.read()
            
        # Execute migration
        logging.info("Applying migration for enriched data tables...")
        await conn.execute(migration_sql)
        logging.info("Migration applied successfully!")
        
        # Verify tables were created
        tables = ['product_nutrition', 'environmental_impact', 'price_history', 'supply_chain']
        for table in tables:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            logging.info(f"Table {table} created successfully (current count: {count})")
            
    except Exception as e:
        logging.error(f"Error applying migration: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_migration()) 