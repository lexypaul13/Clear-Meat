"""Tests for the MeatWise API endpoints."""

from fastapi.testclient import TestClient
import pytest

from app.main import app

client = TestClient(app)


def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "Welcome to the MeatWise API" in response.json()["message"]


def test_read_products():
    """Test the products endpoint."""
    response = client.get("/api/v1/products/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_read_ingredients():
    """Test the ingredients endpoint."""
    response = client.get("/api/v1/ingredients/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_nonexistent_endpoint():
    """Test a nonexistent endpoint."""
    response = client.get("/nonexistent")
    assert response.status_code == 404 