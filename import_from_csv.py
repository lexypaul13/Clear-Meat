#!/usr/bin/env python
import os
import csv
import sys
import psycopg2
from datetime import datetime

# Increase CSV field size limit
maxInt = sys.maxsize
while True:
    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt/10)
print(f"CSV field size limit set to {maxInt}")

# PostgreSQL connection details from environment variables
conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "54322"),
    dbname=os.getenv("DB_NAME", "postgres"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "postgres")
)
cur = conn.cursor()

# Path to the CSV file
csv_file_path = "/Users/alexpaul/Downloads/Clear Meat Products.csv"

# Check if file exists
if not os.path.exists(csv_file_path):
    print(f"ERROR: CSV file not found at {csv_file_path}")
    exit(1)

# Counter for imported products
imported_count = 0
error_count = 0

# Read and process the CSV file
print(f"Starting import from {csv_file_path}...")
with open(csv_file_path, 'r') as file:
    csv_reader = csv.DictReader(file)
    
    for row in csv_reader:
        try:
            # Extract the data from the CSV row
            code = row.get('code', '')
            if not code:
                print("Skipping row without code")
                continue
                
            # Check if product already exists
            cur.execute("SELECT code FROM products WHERE code = %s", (code,))
            if cur.fetchone():
                print(f"Product {code} already exists, skipping")
                continue
            
            # Get the values from the CSV, handling missing ones
            name = row.get('name', '')
            brand = row.get('brand', '')
            description = row.get('description', '')
            ingredients_text = row.get('ingredients_text', '')
            meat_type = row.get('meat_type', '')
            risk_rating = row.get('risk_rating', '')
            image_url = row.get('image_url', '')
            
            # Convert string values to appropriate types
            calories = float(row.get('calories', 0)) if row.get('calories') else None
            protein = float(row.get('protein', 0)) if row.get('protein') else None
            fat = float(row.get('fat', 0)) if row.get('fat') else None
            carbohydrates = float(row.get('carbohydrates', 0)) if row.get('carbohydrates') else None
            salt = float(row.get('salt', 0)) if row.get('salt') else None
            
            # Current timestamp for created_at and last_updated
            now = datetime.now()
            
            # Insert the product into the database
            cur.execute("""
                INSERT INTO products (
                    code, name, brand, description, ingredients_text, 
                    calories, protein, fat, carbohydrates, salt,
                    meat_type, risk_rating, image_url, last_updated, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                code, name, brand, description, ingredients_text,
                calories, protein, fat, carbohydrates, salt,
                meat_type, risk_rating, image_url, now, now
            ))
            
            imported_count += 1
            if imported_count % 100 == 0:
                print(f"Imported {imported_count} products so far")
                conn.commit()  # Commit every 100 products
                
        except Exception as e:
            error_count += 1
            print(f"Error importing row: {e}")
            if error_count > 10:  # Limit the number of errors we show
                print("Too many errors, stopping...")
                break

# Commit any remaining transactions
conn.commit()

# Close the database connection
cur.close()
conn.close()

print(f"Import completed. Imported {imported_count} products with {error_count} errors.") 