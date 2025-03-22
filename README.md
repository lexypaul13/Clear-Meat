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