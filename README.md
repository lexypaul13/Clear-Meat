# MeatWise API

The MeatWise API is a backend application that helps users understand the health implications and additives in meat products by scanning them.

## Project Structure

The project is organized into the following directories:

- `app/`: Core application code
  - `api/`: API endpoints and routes
  - `core/`: Core configuration and settings
  - `db/`: Database connection and models
  - `internal/`: Internal utilities and dependencies
  - `models/`: Data models
  - `routers/`: API routers for different resources
  - `utils/`: Utility functions

- `data/`: Data files
  - `json/`: JSON examples and templates
  - `sql/`: SQL schema and seed data

- `docs/`: Documentation
  - `API_README.md`: Detailed API documentation
  - `PROJECT_TRACKER.md`: Project tracking and progress

- `scripts/`: Utility scripts

- `src/tests/`: Test files
  - `add_test_product.py`: Script to add test products
  - `simple_test.py`: Basic test suite
  - `test_api.py`: API tests

- `supabase/`: Supabase configuration
  - `migrations/`: Database migration files
  - `seed.sql`: Seed data

## Features

- Product scanning
- Health risk assessment
- Additives information
- User accounts
- Favorites and history

## API Endpoints

- `/auth`: Authentication endpoints
- `/users`: User management
- `/products`: Product information
- `/ingredients`: Ingredient details

## Environment Variables

This application requires several environment variables to be set for proper operation. You can create a `.env` file in the root directory of the project with the following variables:

```bash
# Copy .env.example to .env and fill in the required values
cp .env.example .env
```

**Required environment variables:**

- `SECRET_KEY`: A secure random key used for JWT token signing (minimum 32 characters)
  - Generate with: `python -c 'import secrets; print(secrets.token_hex(32))'`
- `SUPABASE_URL`: The URL of your Supabase instance
- `SUPABASE_KEY`: The API key for your Supabase instance

For a complete list of environment variables, see the `.env.example` file.

## Security Features

MeatWise API implements several security best practices:

### Authentication & Authorization
- JWT-based authentication
- Role-Based Access Control with granular permissions
- Token expiration and validation

### Protection Against Common Attacks
- Input validation and sanitization
- Protection against SQL injection
- XSS protection via Content Security Policy headers
- CSRF protection
- Rate limiting to prevent brute force attacks

### Data Security
- Secure password hashing with bcrypt
- Environment-based configuration with .env file
- No hardcoded secrets

### API Security
- Request validation middleware
- Security headers (X-Content-Type-Options, X-Frame-Options, etc.)
- Proper error handling

## Development Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Set up environment variables in `.env`
6. Run the development server: `uvicorn app.main:app --reload`

## License

This project is licensed under the MIT License.

## Database Audit Tools

The project includes a set of database audit tools to help identify and fix potential security and schema issues.

### Available Audit Scripts

1. **Schema Audit** (`scripts/audit_tables.py`) - Audits the database schema for common issues like:
   - Missing primary keys and foreign keys
   - Missing indexes on frequently queried columns
   - Improper data types
   - Tables without proper constraints
   - Column nullability issues

2. **Data Security Audit** (`scripts/data_security_audit.py`) - Identifies data security risks including:
   - Unprotected PII (Personally Identifiable Information)
   - Insecure password storage
   - Missing Row-Level Security (RLS) policies
   - Unanonymized data in test environments
   - Missing audit logging for sensitive data access

3. **Combined Audit Runner** (`scripts/run_db_audit.sh`) - Runs both audits and generates comprehensive reports in JSON and HTML formats.

### Running the Audits

To run all database audits and generate reports:

```bash
./scripts/run_db_audit.sh
```

This will:
- Run both schema and data security audits
- Generate individual JSON reports for each audit
- Create a combined HTML report with all findings
- Automatically open the HTML report in your browser (if supported)

The audit tools use database connection parameters from your `.env` file. If no `.env` file is found, default connection parameters will be used.

### Interpreting Results

Audit issues are categorized by severity:

- **High**: Critical issues that require immediate attention
- **Medium**: Important issues that should be addressed
- **Low**: Suggestions for best practices

The HTML report provides a summary of issues by table/category and detailed recommendations for each finding.

### Custom Audit Parameters

You can also run individual audit scripts with custom parameters:

```bash
# Schema audit
python scripts/audit_tables.py --host localhost --port 5432 --dbname your_db --user your_user --password your_pass --output report.json

# Data security audit
python scripts/data_security_audit.py --host localhost --port 5432 --dbname your_db --user your_user --password your_pass --output report.json
``` 