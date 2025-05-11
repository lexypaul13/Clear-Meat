import csv
import psycopg2
from datetime import datetime
import sys
maxInt = sys.maxsize

while True:
    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt/10)

# Connect to the database
conn = psycopg2.connect(dbname='meatwise')
cur = conn.cursor()

# Read and process the CSV file
with open('/Users/peter/Downloads/products_rows.csv', 'r') as file:
    csv_reader = csv.DictReader(file)
    
    for row in csv_reader:
        # Convert risk_rating to boolean fields
        contains_nitrites = False
        contains_phosphates = False
        contains_preservatives = False
        
        # Check ingredients for additives
        ingredients = row['ingredients_text'].lower() if row['ingredients_text'] else ''
        if 'nitrite' in ingredients or 'nitrate' in ingredients or 'e250' in ingredients or 'e251' in ingredients:
            contains_nitrites = True
        if 'phosphate' in ingredients or 'e338' in ingredients or 'e339' in ingredients:
            contains_phosphates = True
        if 'preservative' in ingredients or 'conservateur' in ingredients:
            contains_preservatives = True
            
        # Convert empty strings to None for numeric fields
        calories = float(row['calories']) if row['calories'] else None
        protein = float(row['protein']) if row['protein'] else None
        fat = float(row['fat']) if row['fat'] else None
        carbs = float(row['carbohydrates']) if row['carbohydrates'] else None
        salt = float(row['salt']) if row['salt'] else None
        
        # Parse timestamps
        def parse_timestamp(ts):
            if not ts:
                return None
            # Remove the '+00' timezone indicator and handle it separately
            ts = ts.replace('+00', '')
            dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')
            return dt
            
        # Insert the data
        try:
            cur.execute("""
                INSERT INTO products (
                    code, name, brand, description, ingredients_text,
                    calories, protein, fat, carbohydrates, salt,
                    meat_type, contains_nitrites, contains_phosphates, contains_preservatives,
                    risk_rating, image_url, last_updated, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                row['code'], row['name'], row['brand'], row['description'], row['ingredients_text'],
                calories, protein, fat, carbs, salt,
                row['meat_type'], contains_nitrites, contains_phosphates, contains_preservatives,
                row['risk_rating'], row['image_url'], 
                parse_timestamp(row['last_updated']),
                parse_timestamp(row['created_at'])
            ))
            conn.commit()
        except Exception as e:
            print(f"Error inserting row {row['code']}: {str(e)}")
            continue

cur.close()
conn.close()

print("Data import completed successfully!") 