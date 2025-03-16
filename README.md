# MeatWise API

A FastAPI-based backend for the MeatWise application, providing information about meat products, their ingredients, and health implications.

## Features

- Fetch meat product data from Open Food Facts
- Store product data in Supabase (PostgreSQL)
- Filter products by various criteria (additives, animal welfare, meat type, risk rating)
- Authentication using Supabase Auth
- AI-powered ingredient analysis
- User history and favorites tracking
- Alternative product recommendations

## Database Schema

The MeatWise application uses Supabase (PostgreSQL) with the following schema:

### Core Tables

- **profiles**: Extends Supabase auth.users to store user preferences and profile information
- **products**: Stores meat product information including nutritional data and risk ratings
- **ingredients**: Contains detailed information about food ingredients and their health implications
- **product_ingredients**: Junction table linking products to their ingredients

### User Interaction Tables

- **scan_history**: Records user product scan history
- **user_favorites**: Stores user's favorite products
- **product_alternatives**: Suggests healthier alternative products

### AI-Related Tables

- **ai_analysis_cache**: Caches results from AI processing to improve performance

### Key Features

- Row-Level Security (RLS) policies to ensure data privacy
- Full-text search indexes for efficient querying
- Vector support (pgvector) for AI similarity searches
- JSON fields for flexible data storage
- Automatic timestamp management

See `database_schema.sql` for the complete schema definition.

## Setup Instructions

### Local Development

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

2. **Configure environment variables**

Create a `.env` file with the following variables:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-key
```

3. **Set up the database**

```bash
python db_setup.py
```

4. **Fetch initial product data**

```bash
python fetch_products.py
```

5. **Run the application**

```bash
uvicorn main:app --reload
```

The API will be available at http://localhost:8000

## API Endpoints

- `GET /product/{barcode}` - Get product details by barcode
- `GET /products/search` - Search for products with filters
- `GET /products/meat-types` - Get all available meat types
- `GET /ingredients/{id}` - Get ingredient details
- `GET /user/history` - Get user scan history
- `GET /user/favorites` - Get user favorites
- `POST /user/favorites/{barcode}` - Add product to favorites
- `DELETE /user/favorites/{barcode}` - Remove product from favorites
- `GET /products/{barcode}/alternatives` - Get healthier alternatives

## Scheduled Updates

To set up weekly data updates from Open Food Facts:

```bash
# Using Supabase Edge Functions
supabase functions deploy update-products
supabase functions schedule update-products --cron "0 0 * * 0"
```

## License

[License information will go here] 