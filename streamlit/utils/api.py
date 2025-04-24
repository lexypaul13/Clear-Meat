import requests
import json
import time
import streamlit as st

# API base URL - replace with your actual API URL in production
BASE_URL = "http://localhost:8001/api/v1"

# Mock data for development
MOCK_DATA = {
    "products": [
        {
            "id": 1,
            "name": "Premium Beef Steak",
            "meat_type": "Beef",
            "price": 15.99,
            "image_url": "https://images.openfoodfacts.org/images/products/327/408/000/5003/front_en.648.400.jpg",
            "nutrition": {
                "protein": "25g",
                "fat": "15g",
                "calories": 280
            },
            "description": "Premium quality beef steak from grass-fed cows. Perfect for grilling or pan-searing."
        },
        {
            "id": 2,
            "name": "Organic Chicken Breast",
            "meat_type": "Poultry",
            "price": 8.99,
            "image_url": "https://images.openfoodfacts.org/images/products/000/000/000/9875/front_en.4.400.jpg",
            "nutrition": {
                "protein": "22g",
                "fat": "3g",
                "calories": 165
            },
            "description": "Organic chicken breast from free-range chickens. Low in fat and high in protein."
        },
        {
            "id": 3,
            "name": "Grass-fed Ground Beef",
            "meat_type": "Beef",
            "price": 7.99,
            "image_url": "https://images.openfoodfacts.org/images/products/843/704/349/1158/front_en.7.400.jpg",
            "nutrition": {
                "protein": "20g",
                "fat": "18g",
                "calories": 250
            },
            "description": "Ground beef from grass-fed cows. Perfect for burgers, meatballs, or any recipe calling for ground beef."
        },
        {
            "id": 4,
            "name": "Pork Tenderloin",
            "meat_type": "Pork",
            "price": 9.99,
            "image_url": "https://images.openfoodfacts.org/images/products/376/020/616/4542/front_fr.93.400.jpg",
            "nutrition": {
                "protein": "26g",
                "fat": "4g",
                "calories": 170
            },
            "description": "Lean and tender pork tenderloin. Great for roasting or grilling."
        },
        {
            "id": 5,
            "name": "Lamb Chops",
            "meat_type": "Lamb",
            "price": 18.99,
            "image_url": "https://images.openfoodfacts.org/images/products/500/015/940/4953/front_fr.56.400.jpg",
            "nutrition": {
                "protein": "20g",
                "fat": "12g",
                "calories": 210
            },
            "description": "Premium lamb chops from grass-fed lambs. Perfect for grilling or roasting."
        },
        {
            "id": 6,
            "name": "Turkey Breast",
            "meat_type": "Poultry",
            "price": 6.99,
            "image_url": "https://images.openfoodfacts.org/images/products/309/264/039/8690/front_fr.24.400.jpg",
            "nutrition": {
                "protein": "24g",
                "fat": "1g",
                "calories": 120
            },
            "description": "Lean turkey breast. Low in fat and high in protein."
        },
        {
            "id": 7,
            "name": "Duck Breast",
            "meat_type": "Duck",
            "price": 12.99,
            "image_url": "https://images.openfoodfacts.org/images/products/20135750/front_en.7.400.jpg",
            "nutrition": {
                "protein": "19g",
                "fat": "12g",
                "calories": 180
            },
            "description": "Premium duck breast. Rich in flavor and perfect for special occasions."
        },
        {
            "id": 8,
            "name": "Venison Steak",
            "meat_type": "Venison",
            "price": 22.99,
            "image_url": "https://images.openfoodfacts.org/images/products/20168144/front_en.4.400.jpg",
            "nutrition": {
                "protein": "26g",
                "fat": "2g",
                "calories": 150
            },
            "description": "Lean venison steak. Low in fat and high in protein with a rich, gamey flavor."
        },
        {
            "id": 9,
            "name": "Turkey Burgers",
            "meat_type": "Poultry",
            "price": 5.99,
            "image_url": "https://images.openfoodfacts.org/images/products/00222629/front_en.3.400.jpg",
            "nutrition": {
                "protein": "20g",
                "fat": "8g",
                "calories": 160
            },
            "description": "Lean turkey burgers. A healthier alternative to beef burgers."
        }
    ]
}

def get_headers():
    """Get headers with authentication token if available"""
    headers = {
        "Content-Type": "application/json"
    }
    
    if "user_data" in st.session_state and "token" in st.session_state.user_data:
        headers["Authorization"] = f"Bearer {st.session_state.user_data['token']}"
    
    return headers

def login(email, password):
    """Login user and return user data with token"""
    
    # TODO: Replace with actual API call in production
    # try:
    #     response = requests.post(
    #         f"{BASE_URL}/auth/login",
    #         headers={"Content-Type": "application/json"},
    #         json={"email": email, "password": password}
    #     )
    #     response.raise_for_status()
    #     return response.json()
    # except requests.RequestException as e:
    #     raise Exception(f"Login failed: {str(e)}")
    
    # Mock response for development
    time.sleep(0.5)  # Simulate API call delay
    
    # Mock login check
    if email == "demo@example.com" and password == "password":
        return {
            "id": 1,
            "name": "Demo User",
            "email": email,
            "token": "mock_jwt_token",
            "preferences": {
                "dietary_preferences": ["Low Carb", "Low Sodium"],
                "cooking_experience": "Intermediate",
                "meat_preferences": ["Beef", "Poultry", "Pork"]
            }
        }
    else:
        raise Exception("Invalid email or password")

def register(name, email, password):
    """Register a new user and return user data with token"""
    
    # TODO: Replace with actual API call in production
    # try:
    #     response = requests.post(
    #         f"{BASE_URL}/auth/register",
    #         headers={"Content-Type": "application/json"},
    #         json={"name": name, "email": email, "password": password}
    #     )
    #     response.raise_for_status()
    #     return response.json()
    # except requests.RequestException as e:
    #     raise Exception(f"Registration failed: {str(e)}")
    
    # Mock response for development
    time.sleep(0.5)  # Simulate API call delay
    
    return {
        "id": 1,
        "name": name,
        "email": email,
        "token": "mock_jwt_token",
        "preferences": {
            "dietary_preferences": [],
            "cooking_experience": "",
            "meat_preferences": []
        }
    }

def save_preferences(preferences):
    """Save user preferences"""
    
    # TODO: Replace with actual API call in production
    # try:
    #     response = requests.post(
    #         f"{BASE_URL}/users/preferences",
    #         headers=get_headers(),
    #         json=preferences
    #     )
    #     response.raise_for_status()
    #     return response.json()
    # except requests.RequestException as e:
    #     raise Exception(f"Failed to save preferences: {str(e)}")
    
    # Mock response for development
    time.sleep(0.5)  # Simulate API call delay
    
    return preferences

def get_products(search_query="", meat_type="All", min_price=0, max_price=50):
    """Get products with optional filtering"""
    
    # TODO: Replace with actual API call in production
    # params = {}
    # if search_query:
    #     params["search"] = search_query
    # if meat_type != "All":
    #     params["meat_type"] = meat_type
    # if min_price > 0:
    #     params["min_price"] = min_price
    # if max_price < 50:
    #     params["max_price"] = max_price
    #
    # try:
    #     response = requests.get(
    #         f"{BASE_URL}/products",
    #         headers=get_headers(),
    #         params=params
    #     )
    #     response.raise_for_status()
    #     return response.json()
    # except requests.RequestException as e:
    #     raise Exception(f"Failed to fetch products: {str(e)}")
    
    # Mock response for development
    time.sleep(0.5)  # Simulate API call delay
    
    products = MOCK_DATA["products"]
    
    # Filter by search query
    if search_query:
        products = [p for p in products if search_query.lower() in p["name"].lower()]
    
    # Filter by meat type
    if meat_type != "All":
        products = [p for p in products if p["meat_type"] == meat_type]
    
    # Filter by price range
    products = [p for p in products if min_price <= p["price"] <= max_price]
    
    return products

def get_product(product_id):
    """Get a single product by ID"""
    
    # TODO: Replace with actual API call in production
    # try:
    #     response = requests.get(
    #         f"{BASE_URL}/products/{product_id}",
    #         headers=get_headers()
    #     )
    #     response.raise_for_status()
    #     return response.json()
    # except requests.RequestException as e:
    #     raise Exception(f"Failed to fetch product: {str(e)}")
    
    # Mock response for development
    time.sleep(0.5)  # Simulate API call delay
    
    for product in MOCK_DATA["products"]:
        if product["id"] == product_id:
            return product
    
    raise Exception(f"Product not found with ID: {product_id}")

def get_recommendations():
    """Get personalized product recommendations"""
    
    # TODO: Replace with actual API call in production
    # try:
    #     response = requests.get(
    #         f"{BASE_URL}/users/recommendations",
    #         headers=get_headers()
    #     )
    #     response.raise_for_status()
    #     return response.json()
    # except requests.RequestException as e:
    #     raise Exception(f"Failed to fetch recommendations: {str(e)}")
    
    # Mock response for development
    time.sleep(0.5)  # Simulate API call delay
    
    # Return a subset of products as recommendations
    # In a real app, this would be based on user preferences
    return MOCK_DATA["products"][:4] 