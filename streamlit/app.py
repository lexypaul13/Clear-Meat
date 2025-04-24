import streamlit as st
import os
import requests
from PIL import Image
import json
import time
import sys

# Add the current directory to the path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import from local modules
try:
    from utils.api import get_products
    from components.product_card import product_grid
except ImportError:
    # Fallback for direct execution
    from streamlit.utils.api import get_products
    from streamlit.components.product_card import product_grid

# Import streamlit extras
try:
    from streamlit_extras.switch_page_button import switch_page
except ImportError:
    # Display error message if streamlit_extras is not installed
    st.error("Required package streamlit_extras is not installed. Please run: pip install streamlit-extras")
    st.stop()

# Configuration
st.set_page_config(
    page_title="MeatWise - Personalized Meat Product Recommendations",
    page_icon="🥩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4a4a4a;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #6b6b6b;
        margin-bottom: 2rem;
    }
    .card {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .btn-primary {
        background-color: #FF4B4B;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        font-size: 1rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Check if user is logged in
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = False

if "user_data" not in st.session_state:
    st.session_state.user_data = {}

if "onboarding_complete" not in st.session_state:
    st.session_state.onboarding_complete = False

# If not authenticated, redirect to login
if not st.session_state.user_authenticated:
    try:
        switch_page("login")
    except Exception as e:
        st.error(f"Error navigating to login page: {e}")
        st.info("Please run this app using 'streamlit run streamlit/app.py' from the project root.")
        st.stop()

# If authenticated but onboarding not complete, redirect to onboarding
elif st.session_state.user_authenticated and not st.session_state.onboarding_complete:
    try:
        switch_page("onboarding")
    except Exception as e:
        st.error(f"Error navigating to onboarding page: {e}")
        st.stop()

# Main app content (Explore page)
else:
    st.markdown('<h1 class="main-header">Explore Meat Products</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Discover personalized meat product recommendations</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### Welcome, {st.session_state.user_data.get('name', 'User')}!")
        st.divider()
        
        # Filters
        st.subheader("Filter Products")
        
        # Meat type filter
        meat_types = ["All", "Beef", "Pork", "Poultry", "Lamb", "Other"]
        selected_meat_type = st.selectbox("Meat Type", meat_types)
        
        # Price range
        price_range = st.slider("Price Range", 0, 50, (0, 30))
        
        # Dietary preferences from user preferences
        st.subheader("Your Preferences")
        preferences = st.session_state.user_data.get('preferences', {})
        
        # Display user preferences
        if preferences:
            for pref_key, pref_value in preferences.items():
                if pref_key == "meat_preferences" and isinstance(pref_value, list):
                    st.write(f"🥩 Preferred Meats: {', '.join(pref_value)}")
                elif pref_key == "cooking_experience":
                    st.write(f"👨‍🍳 Cooking Level: {pref_value}")
                elif pref_key == "dietary_preferences" and isinstance(pref_value, list):
                    st.write(f"🥗 Dietary: {', '.join(pref_value)}")
        
        # Logout button
        if st.button("Logout"):
            st.session_state.user_authenticated = False
            st.session_state.user_data = {}
            st.session_state.onboarding_complete = False
            try:
                switch_page("login")
            except Exception as e:
                st.error(f"Error logging out: {e}")
                st.experimental_rerun()
    
    # Search bar
    search_query = st.text_input("Search for meat products", "")
    
    # Get filtered products
    try:
        filtered_products = get_products(
            search_query=search_query,
            meat_type=selected_meat_type,
            min_price=price_range[0],
            max_price=price_range[1]
        )
    except Exception as e:
        st.error(f"Error fetching products: {e}")
        filtered_products = []
    
    # Handle clicking on a product
    def handle_product_click(product_id):
        st.experimental_set_query_params(id=product_id)
        try:
            switch_page("product_details")
        except Exception as e:
            st.error(f"Error navigating to product details: {e}")
    
    # Display products in a grid
    if not filtered_products:
        st.info("No products match your search criteria.")
    else:
        clicked_product = product_grid(
            filtered_products, 
            columns=3, 
            on_product_click=handle_product_click
        )
        
        # If a product was clicked, navigate to product details
        if clicked_product:
            st.experimental_set_query_params(id=clicked_product)
            try:
                switch_page("product_details")
            except Exception as e:
                st.error(f"Error navigating to product details: {e}")

if __name__ == "__main__":
    st.write("Running app directly. This should be run through Streamlit with 'streamlit run streamlit/app.py'.") 