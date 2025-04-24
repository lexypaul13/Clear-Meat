import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import ssl
from datetime import datetime, timedelta

async def main():
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print('DATABASE_URL not set')
        return
        
    # Create SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Connect to database
    conn = await asyncpg.connect(DATABASE_URL, ssl=ssl_context)
    
    # Get recently updated products
    results = await conn.fetch('''
        SELECT code, name, brand, last_updated 
        FROM products 
        WHERE image_data IS NOT NULL 
        AND last_updated > NOW() - INTERVAL '1 hour'
        ORDER BY last_updated DESC
    ''')
    
    print(f'\nProducts updated with new images in the last hour: {len(results)}\n')
    print('CODE            | BRAND                          | NAME')
    print('-' * 80)
    
    for r in results:
        code = str(r['code'])[:15].ljust(15)
        brand = (str(r['brand']) if r['brand'] else '-')[:30].ljust(30)
        name = str(r['name'])
        print(f'{code} | {brand} | {name}')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main()) 