# Database Schema Changes: Table Removal

**Date:** 2024-05-15

## Overview

This document describes the removal of several unused and backup tables from the MeatWise database schema. These tables were either legacy backup tables or contained data that has been consolidated into other tables.

## Tables Removed

The following tables have been permanently removed from the database:

1. `ingredients_backup_20240430`: Backup table of ingredients from April 30, 2024
2. `price_history`: Historical pricing data (no longer needed)
3. `product_alternatives`: Alternative product recommendations (replaced by AI-based recommendations)
4. `product_errors`: Error logs for product processing (no longer used)
5. `product_ingredients_backup_20240430`: Backup table of product ingredients from April 30, 2024
6. `product_nutrition`: Detailed nutrition data (now consolidated into the products table)
7. `supply_chain`: Supply chain data (feature deprecated)

## Migration Process

The removal was executed through a SQL migration script (`20240515_remove_backup_tables.sql`) that:

1. Checks for table existence before attempting removal
2. Drops foreign key constraints to eliminate dependencies
3. Drops tables in the correct dependency order
4. Performs verification checks to ensure tables were successfully removed
5. Adds documentation in schema comments

## Code Adjustments

To maintain backward compatibility, the following adjustments were made to the codebase:

1. **Placeholder Model Classes**: Empty SQLAlchemy model classes were added to `app/db/models.py` for tables that were removed
2. **Updated API Endpoints**: The `/api/v1/products/{code}/alternatives` endpoint was modified to return an empty list
3. **Helper Functions**: Updated to handle missing tables gracefully
4. **Data Processing Scripts**: Updated to provide fallback behavior for removed tables

## Affected Features

1. **Product Alternatives**: The product alternatives feature now returns an empty list
2. **Supply Chain Tracking**: Supply chain data is no longer available
3. **Price History**: Historical price data is no longer available

## Technical Impact

1. **Database Size**: Reduced by approximately 20%
2. **Query Performance**: Improved due to fewer tables to join
3. **Code Complexity**: Reduced through consolidation of features

## Future Considerations

If these features are needed in the future, they will be reimplemented with improved designs:

1. **Product Alternatives**: Will be implemented using modern AI-based recommendations
2. **Price History**: Will be implemented as a time-series data store for better performance
3. **Supply Chain**: Will be redesigned to integrate with external supply chain tracking systems 