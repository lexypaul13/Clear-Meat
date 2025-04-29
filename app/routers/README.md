# Router Code Cleanup After Table Removal

After running the `20240430_remove_unused_tables.sql` migration, the following code files need to be updated:

## Files to Modify

1. **app/routers/__init__.py**
   - Remove the import for `ingredients` router
   - Remove the line that includes the ingredients router in the API

2. **app/routers/ingredients.py**
   - This entire file should be deleted as it depends on the removed ingredients table

3. **app/db/models.py**
   - Remove the `Ingredient` class
   - Remove the `ProductIngredient` class

4. **app/models/ingredient.py**
   - This file can be deleted (if it exists) or kept for the `AdditiveInfo` class that may still be used

5. **app/routers/products.py**
   - Remove the ingredients query and join in the `get_product` endpoint
   - Update the `AdditiveInfo` import if needed
   - Remove any references to `ingredients` relationship or removed tables

## Code Replacement Strategy

For the `environmental_impact` calculations, the code currently calls `helpers.assess_environmental_impact()`. This helper function should be updated to calculate impact values on-the-fly rather than fetching from the database.

## Testing After Changes

After making these changes, test the following endpoints:

1. `GET /api/v1/products/`
2. `GET /api/v1/products/{code}`

The response should no longer include ingredients lists populated from the database. The `additives` field in responses will likely be an empty array.

## Rollback Strategy

If needed, restore from a database backup and revert the code changes. 