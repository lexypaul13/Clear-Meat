# Supabase Setup Guide for MeatWise

This guide will walk you through setting up a Supabase project for the MeatWise application and deploying the database schema.

## 1. Create a Supabase Project

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Click "New Project"
3. Enter project details:
   - Name: `meatwise`
   - Database Password: (create a secure password)
   - Region: (choose the region closest to your users)
   - Pricing Plan: (select appropriate plan)
4. Click "Create new project"
5. Wait for the project to be created (this may take a few minutes)

## 2. Deploy the Database Schema

### Option 1: Using the SQL Editor

1. In your Supabase project dashboard, go to the "SQL Editor" tab
2. Create a new query
3. Copy the contents of `supabase/migrations/20240316_initial_schema.sql`
4. Paste into the SQL Editor
5. Click "Run" to execute the SQL and create the schema

### Option 2: Using the Supabase CLI

If you have Docker installed and the Supabase CLI set up:

```bash
# Login to Supabase
supabase login

# Link your local project to your Supabase project
supabase link --project-ref <project-id>
# (You can find your project-id in the URL of your Supabase dashboard)

# Push the database schema to your Supabase project
supabase db push
```

## 3. Load Sample Data

1. In your Supabase project dashboard, go to the "SQL Editor" tab
2. Create a new query
3. Copy the contents of `supabase/seed.sql`
4. Paste into the SQL Editor
5. Click "Run" to execute the SQL and load sample data

## 4. Test the API

After deploying the schema and loading sample data, you can test the API:

1. In your Supabase dashboard, go to the "API" tab
2. Under "Tables and Views", you should see all the tables we created
3. Click on a table (e.g., "products") to see the auto-generated API endpoints
4. You can test these endpoints using the provided examples

Example API request to get all products:

```bash
curl 'https://<project-id>.supabase.co/rest/v1/products?select=*' \
  -H "apikey: <anon-key>" \
  -H "Authorization: Bearer <anon-key>"
```

## 5. Get JSON Data for Review

To get the JSON data for review, you can use the Supabase API:

```bash
# Get all products
curl 'https://<project-id>.supabase.co/rest/v1/products?select=*' \
  -H "apikey: <anon-key>" \
  -H "Authorization: Bearer <anon-key>"

# Get all ingredients
curl 'https://<project-id>.supabase.co/rest/v1/ingredients?select=*' \
  -H "apikey: <anon-key>" \
  -H "Authorization: Bearer <anon-key>"

# Get products with their ingredients (using nested select)
curl 'https://<project-id>.supabase.co/rest/v1/products?select=*,product_ingredients(ingredient_id(name,description,risk_level))' \
  -H "apikey: <anon-key>" \
  -H "Authorization: Bearer <anon-key>"
```

Replace `<project-id>` with your Supabase project ID and `<anon-key>` with your anon key from the API settings.

## 6. Next Steps

After reviewing the JSON data:

1. Update the schema if needed by creating new migration files
2. Configure authentication settings in the Supabase dashboard
3. Set up any additional Row Level Security policies
4. Connect your FastAPI application to Supabase using the provided credentials 