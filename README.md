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
   # Create .env file
   touch .env

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
   ./start_local_dev.sh

   # Terminal 2: Start the Streamlit frontend
   streamlit run streamlit/app.py
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
│   ├── models/         # Data models
│   └── utils/          # Utilities
├── streamlit/          # Frontend application
│   ├── app.py         # Main Streamlit app
│   └── components/    # UI components
├── supabase/          # Supabase Configuration
│   ├── migrations/    # Database migrations
│   ├── config.toml   # Supabase settings
│   └── seed.sql      # Initial database data
├── scripts/            # Utility scripts
└── requirements.txt    # Project dependencies
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

## Troubleshooting

1. **Database Connection Issues**
   - Check if Supabase credentials are correct in `.env`
   - Verify network connection to Supabase

2. **Frontend Not Loading**
   - Ensure backend is running on port 8001
   - Check browser console for errors
   - Verify Streamlit installation

3. **Authentication Issues**
   - Clear browser cookies
   - Check JWT_SECRET in `.env`
   - Verify user credentials

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Project Overview

MeatWise is a specialized database and API focused on meat products, providing detailed information about:

### Key Features

- **Specialized Meat Product Database**: Currently tracking 1,161 products across different meat types
- **Smart Description Generation**: Uses Gemini LLM for generating detailed product descriptions
- **Efficient Caching System**: Implements aggressive caching to minimize API costs
- **RAG-Optimized Data**: Structured for effective Retrieval Augmented Generation
- **User-Friendly Frontend**: Streamlit interface for exploring products with personalized recommendations

## Technical Implementation

### Database Structure

- PostgreSQL database with specialized tables for meat products
- Efficient caching system for AI-generated content
- Text similarity indexing for better product matching

### AI Integration

- Uses Google's Gemini for natural language processing
- Implements RAG (Retrieval Augmented Generation) for accurate responses
- Includes caching mechanisms to optimize API usage and costs

### Frontend Implementation

- Multi-page Streamlit interface
- User authentication and personalization
- Onboarding flow for collecting preferences
- Interactive product exploration
- Detailed product views with nutritional information

### Data Structure

#### Product Descriptions
- Original descriptions preserved in `description` column
- Enhanced descriptions stored in `enhanced_description`
- Confidence scoring for AI-generated content
- Timestamp tracking for enhancements

#### Caching System
- Two-level caching strategy:
  - Direct product matches
  - Similar product matches by meat type
- 30-day cache expiration
- Confidence scoring for matches

### Data Quality Statistics
- Total Products: 1,161
- Products with Original Descriptions: 139
- Products Needing Enhancement: 1,022
- Average Description Length: 85 characters
- Description Quality Distribution:
  - High Quality (>200 chars): 12%
  - Medium Quality (100-200 chars): 23%
  - Low Quality (<100 chars): 65%

## Getting Started

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your credentials
3. Install dependencies: `pip install -r requirements.txt`
4. Run migrations: `python scripts/apply_migrations.py`
5. Start the API: `uvicorn app.main:app --reload --port 8001`
6. Start the frontend: `python run_streamlit.py`

## Configuration

Required environment variables:
```env
DATABASE_URL=your_supabase_connection_string
GEMINI_API_KEY=your_gemini_api_key
```

## Development Status

### Completed
- ✅ Initial database schema and migrations
- ✅ Product data collection from Open Food Facts
- ✅ Description enhancement infrastructure
- ✅ Caching system for AI responses
- ✅ Streamlit frontend development

### In Progress
- 🔄 Generating enhanced descriptions using Gemini
- 🔄 RAG implementation for product queries
- 🔄 API endpoint development

### Planned
- ⏳ Frontend integration
- ⏳ User feedback system
- ⏳ Advanced analytics features

## Contributing

Contributions are welcome! Please read our contributing guidelines for details on our code of conduct and the process for submitting pull requests.

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

## Security Best Practices
1. Never commit `.env` files
2. Use environment variables for all secrets
3. Follow the principle of least privilege
4. Enable Row Level Security in Supabase
5. Regularly rotate API keys

## Troubleshooting
- Check if environment variables are properly set
- Verify network connection to Supabase
- Check logs for detailed error messages

## Contributing
1. Create a feature branch
2. Make your changes
3. Submit a pull request

## License
MIT

## Project Overview

MeatWise is a specialized database and API focused on meat products, providing detailed information about:

### Key Features

- **Specialized Meat Product Database**: Currently tracking 1,161 products across different meat types
- **Smart Description Generation**: Uses Gemini LLM for generating detailed product descriptions
- **Efficient Caching System**: Implements aggressive caching to minimize API costs
- **RAG-Optimized Data**: Structured for effective Retrieval Augmented Generation
- **User-Friendly Frontend**: Streamlit interface for exploring products with personalized recommendations

## Technical Implementation

### Database Structure

- PostgreSQL database with specialized tables for meat products
- Efficient caching system for AI-generated content
- Text similarity indexing for better product matching

### AI Integration

- Uses Google's Gemini for natural language processing
- Implements RAG (Retrieval Augmented Generation) for accurate responses
- Includes caching mechanisms to optimize API usage and costs

### Frontend Implementation

- Multi-page Streamlit interface
- User authentication and personalization
- Onboarding flow for collecting preferences
- Interactive product exploration
- Detailed product views with nutritional information

### Data Structure

#### Product Descriptions
- Original descriptions preserved in `description` column
- Enhanced descriptions stored in `enhanced_description`
- Confidence scoring for AI-generated content
- Timestamp tracking for enhancements

#### Caching System
- Two-level caching strategy:
  - Direct product matches
  - Similar product matches by meat type
- 30-day cache expiration
- Confidence scoring for matches

### Data Quality Statistics
- Total Products: 1,161
- Products with Original Descriptions: 139
- Products Needing Enhancement: 1,022
- Average Description Length: 85 characters
- Description Quality Distribution:
  - High Quality (>200 chars): 12%
  - Medium Quality (100-200 chars): 23%
  - Low Quality (<100 chars): 65%

## Getting Started

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your credentials
3. Install dependencies: `pip install -r requirements.txt`
4. Run migrations: `python scripts/apply_migrations.py`
5. Start the API: `uvicorn app.main:app --reload --port 8001`
6. Start the frontend: `python run_streamlit.py`

## Configuration

Required environment variables:
```env
DATABASE_URL=your_supabase_connection_string
GEMINI_API_KEY=your_gemini_api_key
```

## Development Status

### Completed
- ✅ Initial database schema and migrations
- ✅ Product data collection from Open Food Facts
- ✅ Description enhancement infrastructure
- ✅ Caching system for AI responses
- ✅ Streamlit frontend development

### In Progress
- 🔄 Generating enhanced descriptions using Gemini
- 🔄 RAG implementation for product queries
- 🔄 API endpoint development

### Planned
- ⏳ Frontend integration
- ⏳ User feedback system
- ⏳ Advanced analytics features

## Contributing

Contributions are welcome! Please read our contributing guidelines for details on our code of conduct and the process for submitting pull requests.

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

## User Onboarding and Preferences

The MeatWise application includes a comprehensive onboarding process that collects user preferences through six questions:

1. **Nutrition Priorities**: User can select their primary nutritional focus (protein, fat, or salt).
2. **Additives and Preservatives**: User can indicate if they want to avoid preservatives.
3. **Antibiotics and Hormones**: User can specify if they prefer meat from animals raised without antibiotics/hormones.
4. **Sourcing & Animal Diet**: User can indicate if they prefer grass-fed or pasture-raised options.
5. **Typical Cooking Style**: User can select their typical cooking method (grilling, pan-frying, or oven/slow-cooker).
6. **Openness to Alternatives**: User can specify if they're open to trying plant-based meat alternatives.

These preferences are stored in the user's profile and used to personalize recommendations and product insights.

### Running User Preferences Migration

If you're upgrading from a previous version, run the preferences migration script to add support for the new fields:

```bash
# Set up environment variables for Supabase
export SUPABASE_URL="your-supabase-url"
export SUPABASE_KEY="your-supabase-key"

# Run schema migration only
python scripts/run_user_preferences_migration.py

# Run schema migration AND migrate legacy preference data to new format
python scripts/run_user_preferences_migration.py --migrate-data
```

This migration:
- Adds documentation about the new preference fields
- Creates a GIN index for faster JSON queries
- Adds validation for the preference structure
- Provides a data migration function to convert legacy preferences to the new format

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

## Troubleshooting

1. **Database Connection Issues**
   - Check if Supabase credentials are correct in `.env`
   - Verify network connection to Supabase

2. **Frontend Not Loading**
   - Ensure backend is running on port 8001
   - Check browser console for errors
   - Verify Streamlit installation

3. **Authentication Issues**
   - Clear browser cookies
   - Check JWT_SECRET in `.env`
   - Verify user credentials

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.