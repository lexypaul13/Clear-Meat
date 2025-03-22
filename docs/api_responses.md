# MeatWise API Endpoint Responses

This document shows example responses from the MeatWise API endpoints. All endpoints are read-only.

## Products Endpoints

### GET /api/v1/products/

Returns a list of all available products with optional filtering.

```json
[
  {
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
    "code": "1234567890123",
    "last_updated": "2025-03-18T03:47:32.452632Z",
    "created_at": "2025-03-18T03:47:32.452632Z",
    "ingredients": []
  },
  // Additional products...
]
```

### GET /api/v1/products/{code}

Returns detailed information about a specific product.

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
        "concerns": ["Cancer risk", "Blood vessel damage"],
        "alternatives": ["Celery powder", "Cherry powder", "Vitamin C"]
      },
      {
        "name": "Sodium Phosphate",
        "category": "stabilizer",
        "risk_level": "medium",
        "concerns": ["Kidney damage", "Heart issues"],
        "alternatives": ["Potassium phosphate", "Natural brines"]
      },
      {
        "name": "Sodium Erythorbate",
        "category": "preservative",
        "risk_level": "low",
        "concerns": ["Gastrointestinal discomfort"],
        "alternatives": ["Vitamin C", "Citric acid"]
      }
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

### GET /api/v1/products/{code}/alternatives

Returns alternative products for a specific product.

```json
[
  {
    "product_code": "1234567890123",
    "alternative_code": "4567890123456",
    "similarity_score": 0.7,
    "reason": "Lower in preservatives and additives",
    "alternative": {
      "name": "Grass-Fed Ground Beef",
      "brand": "GreenPastures",
      "description": "Ground beef from grass-fed cattle",
      "ingredients_text": "Grass-fed beef",
      "calories": 250.0,
      "protein": 26.0,
      "fat": 17.0,
      "carbohydrates": 0.0,
      "salt": 0.1,
      "meat_type": "beef",
      "contains_nitrites": false,
      "contains_phosphates": false,
      "contains_preservatives": false,
      "antibiotic_free": true,
      "hormone_free": true,
      "pasture_raised": true,
      "risk_rating": "Green",
      "risk_score": 5,
      "image_url": "https://example.com/images/groundbeef.jpg",
      "source": "openfoodfacts",
      "code": "4567890123456",
      "last_updated": "2025-03-18T03:47:32.452632Z",
      "created_at": "2025-03-18T03:47:32.452632Z",
      "ingredients": []
    }
  }
]
```

## Ingredients Endpoints

### GET /api/v1/ingredients/

Returns a list of all ingredients with optional filtering.

```json
[
  {
    "name": "Sodium Nitrite",
    "description": "A preservative commonly used in processed meats",
    "category": "preservative",
    "risk_level": "high",
    "concerns": ["Cancer risk", "Blood vessel damage"],
    "alternatives": ["Celery powder", "Cherry powder", "Vitamin C"],
    "id": "6b42c35a-1975-4305-8449-224a5d2c0ffb",
    "created_at": "2025-03-18T03:47:32.452632Z",
    "updated_at": "2025-03-18T03:47:32.452632Z"
  },
  {
    "name": "Monosodium Glutamate (MSG)",
    "description": "Flavor enhancer commonly used in processed foods",
    "category": "flavor enhancer",
    "risk_level": "medium",
    "concerns": ["Headaches", "Flushing", "Sweating"],
    "alternatives": ["Yeast extract", "Tomatoes", "Mushrooms"],
    "id": "aaa8bd40-3d67-470e-8f7e-4ed5f59cebde",
    "created_at": "2025-03-18T03:47:32.452632Z",
    "updated_at": "2025-03-18T03:47:32.452632Z"
  },
  // Additional ingredients...
]
```

### GET /api/v1/ingredients/{ingredient_id}

Returns detailed information about a specific ingredient.

```json
{
  "name": "Sodium Nitrite",
  "description": "A preservative commonly used in processed meats",
  "category": "preservative",
  "risk_level": "high",
  "concerns": ["Cancer risk", "Blood vessel damage"],
  "alternatives": ["Celery powder", "Cherry powder", "Vitamin C"],
  "id": "6b42c35a-1975-4305-8449-224a5d2c0ffb",
  "created_at": "2025-03-18T03:47:32.452632Z",
  "updated_at": "2025-03-18T03:47:32.452632Z"
}
``` 