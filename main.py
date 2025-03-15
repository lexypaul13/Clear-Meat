from fastapi import FastAPI
import os

from app.routers import root, products
from app.database.database import Base, engine

# Initialize FastAPI app
app = FastAPI(
    title="Meat Products API",
    description="API for retrieving information about meat products from Open Food Facts",
    version="1.0.0"
)

# Include routers
app.include_router(root.router)
app.include_router(products.router)

# Create tables if they don't exist
# Uncomment in development, but in production use migrations
# Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 