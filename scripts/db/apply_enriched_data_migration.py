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
        
        # Verify tables were created - UPDATED: Removed tables that no longer exist
        # NOTE: As of 2024-05-15, product_nutrition, price_history, and supply_chain tables 
        # have been removed. Only verifying environmental_impact table.
        tables = ['environmental_impact']
        for table in tables:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                logging.info(f"Table {table} created successfully (current count: {count})")
            except Exception as e:
                logging.error(f"Error verifying table {table}: {str(e)}")
            
    except Exception as e:
        logging.error(f"Error applying migration: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_migration()) 