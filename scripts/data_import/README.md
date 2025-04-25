# Data Import Scripts

Scripts for importing and enriching product data in the MeatWise database.

## Scripts

### import_from_openfoodfacts.py
Imports meat products from OpenFoodFacts:
- Filters for meat products
- Downloads product data and images
- Handles rate limiting
- Validates data before import

### data_enrichment.py
Enriches product data with additional information:
- Adds nutritional analysis
- Calculates risk ratings
- Enhances product categorization
- Updates metadata

### enhance_descriptions.py
Uses Gemini AI to enhance product descriptions:
- Generates detailed descriptions
- Maintains factual accuracy
- Caches results
- Handles batch processing

### extract_ingredients.py
Extracts and normalizes ingredient information:
- Parses ingredient lists
- Standardizes ingredient names
- Identifies preservatives
- Updates ingredient metadata

## Common Operations

1. **Import New Products**
   ```bash
   python import_from_openfoodfacts.py
   ```

2. **Enrich Existing Data**
   ```bash
   python data_enrichment.py
   ```

3. **Enhance Descriptions**
   ```bash
   python enhance_descriptions.py --batch-size 50
   ```

4. **Update Ingredients**
   ```bash
   python extract_ingredients.py
   ```

## Data Standards

- Product codes must be unique
- All dates in ISO format
- Ingredients in lowercase
- Descriptions in English
- Measurements in metric units 