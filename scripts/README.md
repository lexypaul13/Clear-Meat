# MeatWise Scripts

This directory contains utility scripts for managing the MeatWise API. The scripts are organized by functionality to maintain a clean and efficient codebase.

## Directory Structure

```
scripts/
├── data_import/     # Data import and enrichment
├── images/          # Image processing and management
├── db/             # Database operations
├── audit/          # Security and data auditing
├── maintenance/    # System maintenance
└── utils/          # Shared utilities
```

## Data Import Scripts

Scripts for importing and enriching product data:

- `import_from_openfoodfacts.py`: Imports meat products from OpenFoodFacts
- `data_enrichment.py`: Enriches product data with additional information
- `enhance_descriptions.py`: Uses Gemini to enhance product descriptions
- `extract_ingredients.py`: Extracts and normalizes ingredient information

## Image Management

Consolidated image processing scripts:

- `verify_images.py`: Comprehensive image verification
  - Validates image data integrity
  - Checks image URLs accessibility
  - Reports invalid images
  - Usage: `python scripts/images/verify_images.py`

- `fix_images.py`: Fixes broken or missing images
  - Downloads images from URLs
  - Processes and optimizes images
  - Handles bulk operations with retry logic
  - Usage: `python scripts/images/fix_images.py --batch-size 50 --max-retries 3`

## Database Management

Database maintenance and monitoring:

- `check_db_schemas.py`: Validates database schema
- `check_product.py`: Inspects individual products
- `apply_enriched_data_migration.py`: Applies data migrations

## Audit Tools

Security and data quality tools:

- `data_security_audit.py`: Performs security checks
- `run_db_audit.sh`: Runs comprehensive database audit
- `verify_data.py`: Validates data integrity

## Maintenance

System maintenance utilities:

- `rate_limit_retry.py`: Handles API rate limiting
- `test_api_connection.py`: Tests API connectivity
- `check_credentials.py`: Verifies API credentials

## Utils

Shared utility modules:

- `supabase_client.py`: Supabase client configuration
- Other shared helper functions

## Usage Examples

1. **Verify Product Images**
   ```bash
   python scripts/images/verify_images.py
   ```

2. **Fix Broken Images**
   ```bash
   python scripts/images/fix_images.py --batch-size 50
   ```

3. **Import New Products**
   ```bash
   python scripts/data_import/import_from_openfoodfacts.py
   ```

4. **Run Security Audit**
   ```bash
   ./scripts/audit/run_db_audit.sh
   ```

## Best Practices

1. **Environment Variables**
   - Always use `.env` for configuration
   - Never commit sensitive data
   - Use `load_dotenv()` in scripts

2. **Error Handling**
   - Implement proper logging
   - Use retry mechanisms for network operations
   - Clean up resources in finally blocks

3. **Database Operations**
   - Use connection pooling
   - Implement proper transaction handling
   - Close connections properly

4. **Image Processing**
   - Validate images before processing
   - Implement size and format restrictions
   - Use proper error handling

## Development Guidelines

1. **Adding New Scripts**
   - Place in appropriate directory
   - Follow existing naming conventions
   - Add documentation and usage examples
   - Implement proper logging

2. **Modifying Existing Scripts**
   - Maintain backward compatibility
   - Update documentation
   - Test thoroughly
   - Follow error handling patterns

3. **Code Style**
   - Use type hints
   - Follow PEP 8
   - Add docstrings
   - Use async where appropriate

## Dependencies

Main dependencies used across scripts:

```python
# Core
python-dotenv
asyncio
logging

# Database
asyncpg
supabase

# Image Processing
Pillow
aiohttp

# Utils
tqdm
argparse
```

## Maintenance Notes

- Scripts in `archive/` are kept for reference but should not be used
- Regular audits should be run using audit tools
- Image processing scripts should be run during off-peak hours
- Database operations should be properly scheduled

## Troubleshooting

Common issues and solutions:

1. **Database Connection Issues**
   - Check DATABASE_URL in .env
   - Verify network connectivity
   - Check SSL settings

2. **Image Processing Errors**
   - Verify image URLs accessibility
   - Check disk space for processing
   - Monitor memory usage

3. **Rate Limiting**
   - Use provided retry mechanisms
   - Adjust batch sizes
   - Monitor API quotas 