import os
import psycopg2
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)

def check_products():
    load_dotenv()
    
    # Get database connection details from environment variables
    db_url = os.getenv('DATABASE_URL')
    
    try:
        # Connect to the database
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Get total count
        cur.execute("SELECT COUNT(*) FROM products")
        total_count = cur.fetchone()[0]
        logging.info(f"Total products in database: {total_count}")
        
        # Get count by meat type
        cur.execute("""
            SELECT meat_type, COUNT(*) 
            FROM products 
            GROUP BY meat_type 
            ORDER BY COUNT(*) DESC
        """)
        type_counts = cur.fetchall()
        logging.info("\nProducts by meat type:")
        for meat_type, count in type_counts:
            logging.info(f"{meat_type}: {count}")
        
        # Get count by risk rating
        cur.execute("""
            SELECT risk_rating, COUNT(*) 
            FROM products 
            GROUP BY risk_rating 
            ORDER BY COUNT(*) DESC
        """)
        risk_counts = cur.fetchall()
        logging.info("\nProducts by risk rating:")
        for rating, count in risk_counts:
            logging.info(f"{rating}: {count}")
        
    except Exception as e:
        logging.error(f"Error checking products: {str(e)}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    check_products() 