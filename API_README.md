# MeatWise API Documentation

## Overview
The MeatWise API provides information about meat products, their ingredients, nutritional data, and health/environmental impacts.

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Authentication is not yet implemented. All endpoints are currently public.

## Endpoints

### Products

#### Get All Products
```
GET /products
```

**Query Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Maximum number of records to return (default: 100)
- `meat_type` (string, optional): Filter by meat type
- `risk_rating` (string, optional): Filter by risk rating
- `contains_nitrites` (boolean, optional): Filter by nitrites content
- `contains_phosphates` (boolean, optional): Filter by phosphates content
- `contains_preservatives` (boolean, optional): Filter by preservatives content

**Response:**
```json
[
  {
    "code": "1234567890123",
    "name": "Premium Bacon",
    "brand": "MeatCo",
    "description": "Sliced bacon from pasture-raised pigs",
    "ingredients_text": "Pork, water, salt, sodium phosphate, sodium erythorbate, sodium nitrite",
    "calories": 541.0,
    "protein": 37.0,
    "fat": 42.0,
    "carbohydrates": 1.4,
    "salt": 1.8,
    "meat_type": "pork",
    "contains_nitrites": true,
    "contains_phosphates": true,
    "contains_preservatives": true,
    "antibiotic_free": false,
    "hormone_free": false,
    "pasture_raised": true,
    "risk_rating": "Yellow",
    "risk_score": 50,
    "image_url": "https://example.com/images/bacon.jpg",
    "source": "openfoodfacts",
    "last_updated": "2025-03-18T03:47:32.452632Z",
    "created_at": "2025-03-18T03:47:32.452632Z",
    "ingredients": []
  }
  // ...more products
]
```

#### Get Product Details
```
GET /products/{code}
```

**Parameters:**
- `code` (string, required): Product barcode

**Response:**
```json
{
  "product": {
    "code": "1234567890123",
    "name": "Premium Bacon",
    "brand": "MeatCo",
    "description": "Sliced bacon from pasture-raised pigs",
    "ingredients_text": "Pork, water, salt, sodium phosphate, sodium erythorbate, sodium nitrite",
    "image_url": "https://example.com/images/bacon.jpg",
    "source": "openfoodfacts",
    "meat_type": "pork"
  },
  "criteria": {
    "risk_rating": "Yellow",
    "risk_score": 50,
    "contains_nitrites": true,
    "contains_phosphates": true,
    "contains_preservatives": true,
    "antibiotic_free": false,
    "hormone_free": false,
    "pasture_raised": true,
    "additives": [
      {
        "name": "Sodium Nitrite",
        "category": "preservative",
        "risk_level": "high",
        "concerns": [
          "Cancer risk",
          "Blood vessel damage"
        ],
        "alternatives": [
          "Celery powder",
          "Cherry powder",
          "Vitamin C"
        ]
      }
      // ...more additives
    ]
  },
  "health": {
    "nutrition": {
      "calories": 541.0,
      "protein": 37.0,
      "fat": 42.0,
      "carbohydrates": 1.4,
      "salt": 1.8
    },
    "health_concerns": [
      "High in sodium",
      "Contains nitrites which may form carcinogenic compounds",
      "High fat content",
      "Contains preservatives that may cause health issues",
      "Contains phosphates which may impact kidney health"
    ]
  },
  "environment": {
    "impact": "Medium",
    "details": "Pork production has a moderate environmental impact compared to beef but higher than plant-based proteins.",
    "sustainability_practices": [
      "Pasture-raised which reduces environmental impact",
      "No information available on water usage or carbon footprint"
    ]
  },
  "metadata": {
    "last_updated": "2025-03-18T03:47:32.452632Z",
    "created_at": "2025-03-18T03:47:32.452632Z"
  }
}
```

#### Get Product Alternatives
```
GET /products/{code}/alternatives
```

**Parameters:**
- `code` (string, required): Product barcode

**Response:**
```json
[
  {
    "product_code": "1234567890123",
    "alternative_code": "9876543210987",
    "similarity_score": 0.85,
    "reason": "Lower sodium alternative"
  }
  // ...more alternatives
]
```

#### Create a New Product
```
POST /products
```

**Request Body:**
```json
{
  "code": "9876543210987",
  "name": "Organic Turkey Slices",
  "brand": "HealthyMeat",
  "description": "Organic sliced turkey breast",
  "ingredients_text": "Turkey breast, salt, spices",
  "calories": 120.5,
  "protein": 25.0,
  "fat": 2.0,
  "carbohydrates": 0.0,
  "salt": 0.5,
  "meat_type": "turkey",
  "contains_nitrites": false,
  "contains_phosphates": false,
  "contains_preservatives": false,
  "antibiotic_free": true,
  "hormone_free": true,
  "pasture_raised": true
}
```

**Response:**
A complete Product object

### Ingredients

#### Get All Ingredients
```
GET /ingredients
```

**Query Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Maximum number of records to return (default: 100)
- `category` (string, optional): Filter by category
- `risk_level` (string, optional): Filter by risk level

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Sodium Nitrite",
    "description": "Preservative commonly used in processed meats",
    "category": "preservative",
    "risk_level": "high",
    "concerns": [
      "Cancer risk when combined with amines",
      "Blood vessel dilation"
    ],
    "alternatives": [
      "Celery powder",
      "Cherry powder",
      "Vitamin C"
    ],
    "created_at": "2025-03-18T03:47:32.452632Z",
    "updated_at": "2025-03-18T03:47:32.452632Z"
  }
  // ...more ingredients
]
```

#### Get Ingredient Details
```
GET /ingredients/{ingredient_id}
```

**Parameters:**
- `ingredient_id` (string, required): Ingredient ID

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Sodium Nitrite",
  "description": "Preservative commonly used in processed meats",
  "category": "preservative",
  "risk_level": "high",
  "concerns": [
    "Cancer risk when combined with amines",
    "Blood vessel dilation"
  ],
  "alternatives": [
    "Celery powder",
    "Cherry powder",
    "Vitamin C"
  ],
  "created_at": "2025-03-18T03:47:32.452632Z",
  "updated_at": "2025-03-18T03:47:32.452632Z"
}
```

## Error Handling
The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request
- `404`: Resource not found
- `500`: Server error

Error responses include a detail message:
```json
{
  "detail": "Error message here"
}
```

## Testing
Use the included test scripts to test the API:
- `simple_test.py`: Tests the individual product endpoint
- `test_all_products.py`: Tests the products listing endpoint 