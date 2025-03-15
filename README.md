# Meat Products API

A FastAPI backend that connects to Open Food Facts to collect data on meat-related products and provides an API to access this data.

## Features

- Fetch meat product data from Open Food Facts
- Store product data in a PostgreSQL database
- Filter products by various criteria (additives, animal welfare, meat type, risk rating)
- Authentication using Firebase
- Deployed on Google Cloud Platform (Cloud Run + Cloud SQL)

## Setup Instructions

### Local Development

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

2. **Configure environment variables**

Create a `.env` file with the following variables:

```
DATABASE_URL=postgresql://username:password@host:5432/meatproducts
FIREBASE_CREDENTIALS_PATH=path/to/firebase-credentials.json
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

### Google Cloud Platform Deployment

1. **Create a Cloud SQL PostgreSQL instance**

```bash
gcloud sql instances create meatproducts-db \
  --database-version=POSTGRES_13 \
  --tier=db-f1-micro \
  --region=us-central1
```

2. **Create a database and user**

```bash
gcloud sql databases create meatproducts --instance=meatproducts-db
gcloud sql users create meatproducts-user --instance=meatproducts-db --password=YOUR_PASSWORD
```

3. **Build and deploy to Cloud Run**

```bash
gcloud builds submit --tag gcr.io/[PROJECT_ID]/meat-products-api
gcloud run deploy meat-products-api \
  --image gcr.io/[PROJECT_ID]/meat-products-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="DATABASE_URL=postgresql://meatproducts-user:YOUR_PASSWORD@/meatproducts?host=/cloudsql/[PROJECT_ID]:us-central1:meatproducts-db"
```

## API Endpoints

- `GET /product/{barcode}` - Get product details by barcode
- `GET /products/search` - Search for products with filters
- `GET /products/meat-types` - Get all available meat types

## Database Schema

The `products` table contains the following fields:

- `code` (primary key) - Product barcode
- `name` - Product name
- `ingredients` - List of ingredients
- `calories`, `protein`, `fat`, `carbohydrates`, `salt` - Nutritional information
- `meat_type` - Type of meat (beef, chicken, pork, seafood)
- `contains_nitrites`, `contains_phosphates`, `contains_preservatives` - Additive flags
- `antibiotic_free`, `hormone_free`, `pasture_raised` - Animal welfare criteria
- `risk_rating` - Risk rating (Green, Yellow, Red)
- `last_updated` - Timestamp of last update
- `image_url` - URL to product image

## Scheduled Updates

To set up weekly data updates, create a Cloud Scheduler job:

```bash
gcloud scheduler jobs create http update-meat-products \
  --schedule="0 0 * * 0" \
  --uri="https://[CLOUD_RUN_URL]/admin/update-products" \
  --http-method=POST \
  --headers="Authorization=Bearer [YOUR_SECRET_KEY]"
``` 