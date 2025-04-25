# Database Management Scripts

Scripts for managing and monitoring the MeatWise database.

## Scripts

### check_db_schemas.py
Validates database schema integrity:
- Checks table structures
- Validates constraints
- Verifies indexes
- Reports inconsistencies

### check_product.py
Tool for inspecting individual products:
- Retrieves complete product data
- Shows relationships
- Validates data integrity
- Reports issues

### apply_enriched_data_migration.py
Applies data migrations safely:
- Handles schema updates
- Migrates data
- Validates results
- Provides rollback capability

## Common Operations

1. **Check Database Schema**
   ```bash
   python check_db_schemas.py
   ```

2. **Inspect Product**
   ```bash
   python check_product.py --code PRODUCT_CODE
   ```

3. **Apply Migration**
   ```bash
   python apply_enriched_data_migration.py
   ```

## Database Standards

- Use prepared statements
- Implement proper transactions
- Handle connection pooling
- Follow naming conventions
- Document schema changes

## Best Practices

1. **Before Running Migrations**
   - Backup database
   - Test in staging
   - Schedule maintenance window
   - Prepare rollback plan

2. **Monitoring**
   - Check connection pools
   - Monitor query performance
   - Watch for deadlocks
   - Track data growth

3. **Security**
   - Use connection pooling
   - Implement proper access control
   - Regular security audits
   - Monitor suspicious activity 