import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import ssl
import base64
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    try:
        # Load environment variables
        load_dotenv()
        
        # Get database URL
        DATABASE_URL = os.getenv('DATABASE_URL')
        if not DATABASE_URL:
            logger.error('DATABASE_URL not set')
            return
            
        logger.info(f"Connecting to database...")
        
        # Create SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL, ssl=ssl_context)
        logger.info("Connected successfully")
        
        # Get recently updated products with image data
        logger.info("Fetching updated products...")
        results = await conn.fetch('''
            SELECT code, name, brand, image_data, last_updated 
            FROM products 
            WHERE image_data IS NOT NULL 
            AND last_updated > NOW() - INTERVAL '1 hour'
            ORDER BY last_updated DESC
        ''')
        
        logger.info(f"Found {len(results)} products with images")
        
        if not results:
            logger.warning("No products found with images in the last hour")
            return
        
        # Generate HTML
        logger.info("Generating HTML...")
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Updated Products Gallery</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; }
                .header { text-align: center; margin-bottom: 30px; }
                .products { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }
                .product { 
                    background: white;
                    padding: 15px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .product img { 
                    width: 100%;
                    height: 200px;
                    object-fit: contain;
                    margin-bottom: 10px;
                    background: #f8f8f8;
                }
                .product h3 { margin: 0 0 5px 0; font-size: 16px; }
                .product p { margin: 0; color: #666; font-size: 14px; }
                .timestamp { color: #999; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Updated Products Gallery</h1>
                    <p>Total products with new images: ''' + str(len(results)) + '''</p>
                    <p>Generated on: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</p>
                </div>
                <div class="products">
        '''
        
        # Add products to HTML
        products_added = 0
        for r in results:
            try:
                image_data = r['image_data']
                if image_data:
                    html += f'''
                    <div class="product">
                        <img src="data:image/jpeg;base64,{image_data}" alt="{r['name']}">
                        <h3>{r['name']}</h3>
                        <p>{r['brand'] if r['brand'] else 'No brand'}</p>
                        <p class="timestamp">Updated: {r['last_updated'].strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                    '''
                    products_added += 1
            except Exception as e:
                logger.error(f"Error processing product {r['code']}: {str(e)}")
        
        html += '''
                </div>
            </div>
        </body>
        </html>
        '''
        
        # Save HTML file
        output_path = 'product_gallery.html'
        with open(output_path, 'w') as f:
            f.write(html)
        
        logger.info(f"Generated gallery with {products_added} products")
        logger.info(f"Saved as {output_path}")
        
        await conn.close()
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 