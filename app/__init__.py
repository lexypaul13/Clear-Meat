"""Setup API."""
from fastapi import FastAPI
from app.models import Product, AdditiveInfo

app = FastAPI(
    title="MeatWise API",
    description="Backend API for MeatWise products",
    version="0.1.0",
)

from app.api.routes import (
    auth,
    users,
)

app.include_router(auth.router)
app.include_router(users.router) 