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