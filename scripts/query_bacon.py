import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to the database
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

try:
    # Query bacon products
    cur.execute("""
        SELECT 
            code, name, brand, description, meat_type, 
            risk_rating, risk_score, contains_nitrites, 
            contains_phosphates
        FROM products 
        WHERE LOWER(name) LIKE '%bacon%'
        LIMIT 5;
    """)
    
    # Print results
    print("\nBacon Products Found:\n")
    rows = cur.fetchall()
    
    if not rows:
        print("No bacon products found.")
    else:
        for row in rows:
            print(f"Name: {row[1]}")
            print(f"Brand: {row[2] or 'Unknown'}")
            print(f"Description: {row[3] or 'Not available'}")
            print(f"Meat Type: {row[4]}")
            print(f"Risk Rating: {row[5]}")
            print(f"Risk Score: {row[6]}")
            print(f"Contains Nitrites: {row[7]}")
            print(f"Contains Phosphates: {row[8]}")
            print("-" * 80)
            print()

finally:
    # Close database connection
    cur.close()
    conn.close() 