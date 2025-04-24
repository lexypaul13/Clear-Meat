# MeatWise API

A backend API service that provides personalized meat product recommendations and insights based on user preferences and scan history.

## Features

- **Product Scanning**: Scan meat products and get detailed information
- **Personalized Insights**: Receive health and ethical insights based on your preferences
- **Product Recommendations**: Get personalized product recommendations using Gemini AI
- **Scan History**: Keep track of all your previously scanned products
- **Streamlit Frontend**: User-friendly web interface for exploring meat products

## Tech Stack

- FastAPI
- PostgreSQL (with Supabase)
- Google Gemini AI
- JWT Authentication
- Pydantic for data validation
- Streamlit for frontend

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL database
- Google Gemini API key

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/meat-products-api.git
   cd meat-products-api
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables by creating a `.env` file:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/meatwise
   JWT_SECRET=your_jwt_secret
   GEMINI_API_KEY=your_gemini_api_key
   ```

### Running the API

Start the FastAPI server:
```
uvicorn app.main:app --reload --port 8001
```

The API will be available at `http://localhost:8001`.

API documentation is automatically generated at:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

### Running the Streamlit Frontend

Start the Streamlit frontend using the provided launcher script:
```
python run_streamlit.py
```

Alternatively, you can run Streamlit directly:
```
streamlit run streamlit/app.py
```

The frontend will be available at `http://localhost:8501` by default.

## API Endpoints

- `/api/v1/auth/register` - Register a new user
- `/api/v1/auth/login` - Authenticate a user
- `/api/v1/users/preferences` - Get/update user preferences
- `/api/v1/users/history` - Get scan history or add new scan
- `/api/v1/users/recommendations` - Get product recommendations
- `/api/v1/users/explore` - Get AI-powered personalized recommendations

## Deployment

For production deployment:

1. Set appropriate environment variables
2. Use Gunicorn as a process manager:
   ```
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
   ```

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

## Product Image Management Tools

The repository includes several scripts to manage product images, fix broken image links, and monitor image status.

### Image Fixing Scripts

1. **Basic Image Fix** - Process individual products:
   ```
   python scripts/fix_broken_images.py --url SUPABASE_URL --key SUPABASE_KEY [--limit NUMBER]
   ```

2. **Bulk Image Fix** - Process all products with missing images in batches:
   ```
   python scripts/fix_broken_images_bulk.py --url SUPABASE_URL --key SUPABASE_KEY [--batch-size SIZE] [--max-workers NUMBER]
   ```

3. **Display Images** - Generate HTML to view updated product images:
   ```
   python scripts/display_images.py --url SUPABASE_URL --key SUPABASE_KEY
   ```

### Monitoring and Management

1. **Dashboard** - Interactive dashboard to monitor image status and updates:
   ```
   python scripts/dashboard.py --url SUPABASE_URL --key SUPABASE_KEY
   ```

2. **Scheduler** - Automate image updates at regular intervals:
   ```
   # Start scheduler to run every 24 hours
   python scripts/scheduler.py --url SUPABASE_URL --key SUPABASE_KEY
   
   # Run with custom interval (in hours)
   python scripts/scheduler.py --url SUPABASE_URL --key SUPABASE_KEY --interval 12
   
   # Run an image update immediately
   python scripts/scheduler.py --url SUPABASE_URL --key SUPABASE_KEY --run-now
   
   # Check scheduler status
   python scripts/scheduler.py --url SUPABASE_URL --key SUPABASE_KEY --status
   ```

3. **Image Statistics** - Get statistics about product images:
   ```
   python scripts/supabase_image_stats.py --url SUPABASE_URL --key SUPABASE_KEY
   ```

## Dependencies

- FastAPI: Web framework
- SQLAlchemy: ORM
- Pydantic: Data validation
- Supabase: Database access
- BeautifulSoup4: Web scraping
- Pandas/Matplotlib: Data analysis and visualization
- TKinter: GUI dashboard
- Schedule: Task scheduling

## Testing

Run tests with:
```
pytest
```