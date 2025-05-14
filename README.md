# MeatWise API

A backend API service that provides personalized meat product recommendations and insights based on user preferences and scan history.

## Quick Start

1. **Clone and Setup**
   ```bash
   # Clone the repository
   git clone https://github.com/yourusername/meat-products-api.git
   cd meat-products-api

   # Create and activate virtual environment
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   # Either create a .env file manually
   touch .env

   # Or use the provided script to create it interactively
   ./scripts/startup/create_new_env.sh

   # Or copy an environment template
   cp scripts/env/.env.example .env

   # Add these variables to .env for local development:
   DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
   SUPABASE_URL=http://localhost:54321
   SUPABASE_KEY=your-supabase-anon-key-here
   JWT_SECRET=your-super-secret-jwt-token-with-at-least-32-characters-long
   API_V1_STR=/api/v1
   ```

3. **Start Supabase Locally**
   ```bash
   # Navigate to Supabase directory
   cd supabase

   # Start Supabase services
   supabase start
   
   # This will start:
   # - PostgreSQL on port 54322
   # - Supabase API on port 54321
   # - Studio on port 54323
   ```

4. **Run the Project**
   ```bash
   # Return to project root if needed
   cd ..

   # IMPORTANT: Use the provided script to start the API server
   # This ensures the correct DATABASE_URL is used regardless of your environment
   ./start_app.py
   
   # Alternatively, you can specify environment and other options
   ./start_app.py --env local --reload
   ./start_app.py --env production --port 8080

   # If you prefer the shell script directly
   ./scripts/startup/start_local_dev.sh
   ```

5. **Access the Application**
   - Backend API: http://localhost:8001
   - API Documentation: http://localhost:8001/docs
   - Frontend: http://localhost:8501
   - Supabase Studio: http://localhost:54323

## Running in Test Mode

The API includes a special test mode that skips database operations when the `TESTING` environment variable is set. This is useful for:

1. **Running Tests**: Execute tests without needing a database connection
2. **Developing Offline**: Work on API functionality without Supabase/PostgreSQL
3. **CI/CD Pipelines**: Run automated tests in build environments

### How to Use Test Mode

1. **Set the Environment Variable**
   ```bash
   # For Linux/macOS
   export TESTING=true
   
   # For Windows PowerShell
   $env:TESTING="true"
   
   # For Windows Command Prompt
   set TESTING=true
   ```

2. **Run the Application**
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```

3. **Test Endpoints**
   
   When running in test mode:
   - Database operations are skipped
   - Endpoints return mock responses where appropriate
   - Health check endpoint reports `{"status": "healthy", "database": "connected", "mode": "testing"}`
   - Authentication flows work without database connection

4. **Run Integration Tests**
   ```bash
   # With TESTING=true set
   pytest tests/
   ```

### Supported Endpoints in Test Mode

The following endpoints fully support test mode:

- **Auth**: `/api/v1/auth/login`, `/api/v1/auth/register`
- **Products**: `/api/v1/products`, `/api/v1/products/{code}`, `/api/v1/products/{code}/report`, `/api/v1/products/{code}/alternatives`
- **Users**: `/api/v1/users/me` (PUT)
- **Health**: `/health/db`

### Example Test Request

```bash
# Test the products endpoint in test mode
curl -X GET "http://localhost:8001/api/v1/products/12345678" -H "accept: application/json"
```

## Supabase Local Development

The project uses Supabase for the database and authentication. The local setup includes:

1. **Database**: PostgreSQL running on port 54322
   - Default user: `postgres`
   - Default password: `postgres`
   - Database name: `postgres`

2. **API**: Supabase API running on port 54321
   - Default JWT token included in `.env`
   - All API features available locally

3. **Studio**: Web interface on port 54323
   - Manage database
   - View API documentation
   - Monitor realtime subscriptions

4. **Data Migration**
   ```bash
   # Apply database migrations
   cd supabase
   supabase migration up
   
   # Load initial data
   supabase db reset
   ```

## Features

- **Product Scanning**: Scan meat products and get detailed information
- **Personalized Insights**: Receive health and ethical insights based on your preferences
- **Product Recommendations**: Get personalized product recommendations
- **Scan History**: Keep track of all your previously scanned products
- **Streamlit Frontend**: User-friendly web interface for exploring meat products

## Tech Stack

- FastAPI
- PostgreSQL (with Supabase)
- JWT Authentication
- Pydantic
- Streamlit
- BeautifulSoup4

## Project Structure

```
meat-products-api/
├── app/                 # Backend API
│   ├── api/            # API endpoints
│   ├── db/             # Database connections and models
│   ├── models/         # Data models
│   └── utils/          # Utilities
├── tests/               # Test suite
│   ├── api/            # API tests
│   ├── db/             # Database tests
│   └── utils/          # Test utilities
├── scripts/             # Utility scripts
│   ├── db/             # Database scripts
│   ├── env/            # Environment templates
│   ├── startup/        # Application startup scripts
│   └── switch_env.py   # Environment switcher
├── supabase/           # Supabase Configuration
│   ├── migrations/     # Database migrations
│   ├── config.toml     # Supabase settings
│   └── seed.sql        # Initial database data
├── docs/                # Documentation
├── start_app.py         # Main application starter
└── requirements.txt     # Project dependencies
```

## API Endpoints

- **Authentication**
  - POST `/api/v1/auth/register`: Register new user
  - POST `/api/v1/auth/login`: Login user

- **Users**
  - GET `/api/v1/users/me`: Get current user
  - PUT `/api/v1/users/preferences`: Update preferences

- **Products**
  - GET `/api/v1/products`: List products
  - GET `/api/v1/products/{id}`: Get product details
  - GET `/api/v1/products/recommendations`: Get recommendations

## User Onboarding and Preferences

The MeatWise application includes a comprehensive onboarding process that collects user preferences through six questions:

1. **Nutrition Priorities**: User can select their primary nutritional focus (protein, fat, or salt).
2. **Additives and Preservatives**: User can indicate if they want to avoid preservatives.
3. **Antibiotics and Hormones**: User can specify if they prefer meat from animals raised without antibiotics/hormones.
4. **Sourcing & Animal Diet**: User can indicate if they prefer grass-fed or pasture-raised options.
5. **Typical Cooking Style**: User can select their typical cooking method (grilling, pan-frying, or oven/slow-cooker).
6. **Openness to Alternatives**: User can specify if they're open to trying plant-based meat alternatives.

These preferences are stored in the user's profile and used to personalize recommendations and product insights.

## Personalized Recommendations

MeatWise implements a sophisticated personalized recommendation system based on user preferences collected during onboarding:

### Enhanced Rule-Based Weighted Scoring

The explore endpoint uses an advanced, rule-based weighted scoring algorithm that:

1. **Normalizes Product Attributes**:
   - Nutritional values (protein, fat, sodium) are normalized against the maximum values in the dataset
   - This ensures fair scoring across different scales and product types

2. **Balanced Weighting System**:
   - Base weights are set for all factors (protein, fat, sodium, etc.)
   - Weights are dynamically adjusted based on user preferences
   - No single factor can dominate the final score
   - Preference-specific weights increase by 50% when a user indicates a strong preference

3. **Diversity Factor**:
   - Ensures representation of different meat types in recommendations
   - Allocates slots fairly across preferred meat types
   - Maintains at least one product per preferred meat type
   - Fills remaining slots with highest-scoring products

4. **Scoring Formula**:
   ```
   score = (w_protein * protein_normalized) +
           (w_fat * (1 - fat_normalized)) +
           (w_sodium * (1 - sodium_normalized)) +
           (w_antibiotic * antibiotic_free) +
           (w_grass * pasture_raised) +
           (w_preservatives * preservative_free) +
           (1.5 * meat_type_match)
   ```

5. **Increased Product Limit**:
   - Returns up to 30 products for better representation
   - Provides more diverse recommendations
   - Allows users to explore a wider range of options

### Benefits

This enhanced recommendation approach provides:
- **Fair Representation**: All meat types get fair consideration
- **Balanced Scoring**: No single factor dominates the recommendations
- **Personalization**: Direct mapping from user preferences to recommendations
- **Diversity**: Ensures variety in recommended products
- **Transparency**: Clear explanation of scoring factors
- **Efficiency**: Fast performance with minimal computational overhead


## Authentication Troubleshooting Guide

When setting up the MeatWise API, you might encounter authentication issues if the environment variables are not properly configured. Here's a guide to avoid common authentication problems:

### Required Environment Variables

Ensure these critical variables are set in your `.env` file:

```bash
# Database Connection
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres

# Supabase Configuration
SUPABASE_URL=http://localhost:54321
SUPABASE_KEY=<your-supabase-anon-key>
SUPABASE_SERVICE_KEY=<your-supabase-service-key>  # Required for admin operations

# JWT Authentication
SECRET_KEY=<your-secret-key-at-least-32-characters>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # Token validity period in minutes
```

### Avoiding Test Mode Issues

The `start_local_dev.sh` script includes test mode, which is useful for development but has limitations:

1. **User Registration:** Test mode disables actual user registration in the database
2. **Database Operations:** Many endpoints will return mock data instead of actual database records

To use the API with the full database functionality:

```bash
# Edit start_local_dev.sh and comment out or remove this line:
# export TESTING=true

# Or override it when running the script
TESTING=false ./start_local_dev.sh
```

### Authentication Flow

For proper authentication:

1. **Register a User First:**
   ```bash
   curl -X POST "http://localhost:8001/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "SecurePassword123!", "full_name": "Example User"}'
   ```

2. **Login to Get Token:**
   ```bash
   curl -X POST "http://localhost:8001/api/v1/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=user@example.com&password=SecurePassword123!"
   ```

3. **Use Token for Authenticated Requests:**
   ```bash
   curl -X GET "http://localhost:8001/api/v1/products" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```

### Common Issues and Solutions

1. **"User registration disabled" Error:**
   - Ensure TESTING environment variable is set to "false" or not set at all
   - Check that SUPABASE_SERVICE_KEY is correctly set in your .env file

2. **"Could not validate credentials" Error:**
   - Verify SECRET_KEY and ALGORITHM are correctly set
   - Ensure your access token is valid and not expired
   - Include the token with "Bearer " prefix in Authorization header

3. **Database Connection Timeout:**
   - Increase timeout settings in your startup script (already included in start_local_dev.sh)
   - Verify PostgreSQL is running and accessible

4. **JWT Token Invalid:**
   - Ensure you're using the latest token from a successful login
   - Check that your SECRET_KEY hasn't changed since the token was issued





```
# Active environment configuration
ENVIRONMENT=development
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/meatwise
SUPABASE_URL=http://localhost:54321
SUPABASE_KEY=your-local-key

# Production configuration (stored but not active)
PRODUCTION_DATABASE_URL=your-production-db-url
PRODUCTION_SUPABASE_URL=your-production-supabase-url
PRODUCTION_SUPABASE_KEY=your-production-key
```

The environment switcher script will preserve both sets of credentials and switch between them as needed.

### Simple Starter Script

For convenience, a starter script is provided that handles both environment switching and starting the API:

```bash
# Start in local environment (default)
./start_app.py

# Start in production environment
./start_app.py --env production

# Start with auto-reload for development
./start_app.py --reload

# Start on a different port
./start_app.py --port 8080
```

This script combines environment switching and server startup in a single command. Under the hood, it uses `scripts/switch_env.py` to set up the environment and then starts the API server with the appropriate configuration.