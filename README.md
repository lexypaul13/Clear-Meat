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
   SUPABASE_KEY=***REMOVED***
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
   # Terminal 1: Start the FastAPI backend
   uvicorn app.main:app --reload --port 8001

   # Terminal 2: Start the Streamlit frontend
   streamlit run streamlit/app.py
   ```

5. **Access the Application**
   - Backend API: http://localhost:8001
   - API Documentation: http://localhost:8001/docs
   - Frontend: http://localhost:8501
   - Supabase Studio: http://localhost:54323

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
- Product descriptions and ingredients
- Nutritional information
- Risk ratings and preservative content
- Processing methods and quality indicators

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
  - `