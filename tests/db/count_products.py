from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Supabase credentials
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY environment variables not set")
    exit(1)

# Initialize Supabase client
supabase = create_client(url, key)

# Get total count
total_response = supabase.table('products').select('*', count='exact').execute()
total_count = total_response.count

print(f"\nTotal number of products: {total_count}")

# Get count by meat type
meat_type_response = supabase.table('products').select('meat_type').execute()
meat_types = {}
for item in meat_type_response.data:
    meat_type = item.get('meat_type', 'Unknown')
    if meat_type in meat_types:
        meat_types[meat_type] += 1
    else:
        meat_types[meat_type] = 1

print("\nProducts by meat type:")
for meat_type, count in meat_types.items():
    print(f"{meat_type}: {count}")

# Get count by risk rating
risk_rating_response = supabase.table('products').select('risk_rating').execute()
risk_ratings = {}
for item in risk_rating_response.data:
    risk_rating = item.get('risk_rating', 'Unknown')
    if risk_rating in risk_ratings:
        risk_ratings[risk_rating] += 1
    else:
        risk_ratings[risk_rating] = 1

print("\nProducts by risk rating:")
for risk_rating, count in risk_ratings.items():
    print(f"{risk_rating}: {count}") 