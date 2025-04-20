import os
from supabase import create_client

# Get Supabase credentials from environment
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY environment variables not set")
    exit(1)

supabase = create_client(url, key)

# Query the products table for the specific product code
product_code = "737628064502"
response = supabase.table("products").select("*").eq("code", product_code).execute()

# Print the result
data = response.data
if data and len(data) > 0:
    print(f"Product exists: True")
    print(f"Product name: {data[0].get('name')}")
else:
    print(f"Product exists: False") 