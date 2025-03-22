# MeatWise API

API backend for the MeatWise application, which helps users scan meat products to understand their health implications and additives.

## Project Structure

The project follows a clean architecture pattern with the following directory structure:

```
app/
├── core/               # Core configuration and utilities
│   ├── config.py       # Application configuration settings
│   └── security.py     # Security utilities (JWT, password hashing)
├── db/                 # Database related code
│   ├── models.py       # SQLAlchemy ORM models
│   └── session.py      # Database session management
├── internal/           # Internal utilities and dependencies
│   ├── dependencies.py # FastAPI dependencies (auth, etc.)
│   └── utils.py        # Utility functions
├── models/             # Pydantic models for request/response
│   ├── product.py      # Product schemas
│   ├── ingredient.py   # Ingredient schemas
│   └── user.py         # User and auth schemas
├── routers/            # API routes/endpoints
│   ├── auth.py         # Authentication endpoints
│   ├── products.py     # Product endpoints
│   ├── ingredients.py  # Ingredient endpoints
│   └── users.py        # User-related endpoints
├── utils/              # Utility modules
│   └── auth.py         # Additional auth utilities
└── main.py             # Application entry point
```

## Features

- Product scanning and lookup by barcode
- Detailed information about meat product ingredients
- Risk assessment for meat products
- User accounts with history tracking
- Favorites management

## API Endpoints

- **Auth**: `/api/v1/auth/login`, `/api/v1/auth/register`
- **Users**: `/api/v1/users/me`, `/api/v1/users/history`, `/api/v1/users/favorites`
- **Products**: `/api/v1/products/`, `/api/v1/products/{barcode}`
- **Ingredients**: `/api/v1/ingredients/`, `/api/v1/ingredients/{id}`

## Development Setup

1. Clone the repository
2. Set up a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with required environment variables:
```
DATABASE_URL=postgresql://username:password@localhost:5432/meatwise
SECRET_KEY=your_secret_key
API_V1_STR=/api/v1
ACCESS_TOKEN_EXPIRE_MINUTES=60
PROJECT_NAME=MeatWise
PROJECT_VERSION=0.1.0
```

5. Run the development server:
```bash
uvicorn app.main:app --reload
```

6. Access the API documentation at `http://localhost:8000/api/v1/docs`

## License

This project is licensed under the MIT License - see the LICENSE file for details. 