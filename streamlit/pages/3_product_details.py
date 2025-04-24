import streamlit as st
import sys
import os
from streamlit_extras.switch_page_button import switch_page

# Add the parent directory to sys.path to import utils
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.api import get_product, get_recommendations

# Configuration
st.set_page_config(
    page_title="MeatWise - Product Details",
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
    .product-container {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .nutrition-label {
        background-color: white;
        border: 1px solid #ddd;
        padding: 15px;
        border-radius: 5px;
    }
    .nutrition-header {
        font-size: 1.2rem;
        font-weight: bold;
        border-bottom: 8px solid #000;
        padding-bottom: 5px;
        margin-bottom: 10px;
    }
    .nutrition-item {
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        border-bottom: 1px solid #ddd;
    }
    .section-header {
        font-size: 1.5rem;
        margin: 20px 0 10px 0;
        padding-bottom: 5px;
        border-bottom: 2px solid #f0f0f0;
    }
    .recommendation-card {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        margin-bottom: 15px;
        height: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = False

if "user_data" not in st.session_state:
    st.session_state.user_data = {}

if "onboarding_complete" not in st.session_state:
    st.session_state.onboarding_complete = False

# Check if user is not authenticated, redirect to login
if not st.session_state.user_authenticated:
    switch_page("login")

# Check if onboarding is not complete, redirect to onboarding
if not st.session_state.onboarding_complete:
    switch_page("onboarding")

# Check if product_id is in query params
query_params = st.experimental_get_query_params()
product_id = None

if "id" in query_params and query_params["id"]:
    try:
        product_id = int(query_params["id"][0])
    except ValueError:
        st.error("Invalid product ID")
        st.stop()

# If no product_id, redirect to main page
if not product_id:
    st.error("No product selected")
    if st.button("Go to Products"):
        switch_page("app")
    st.stop()

# Attempt to get the product
try:
    product = get_product(product_id)
except Exception as e:
    st.error(f"Error: {str(e)}")
    if st.button("Go to Products"):
        switch_page("app")
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown(f"### Welcome, {st.session_state.user_data.get('name', 'User')}!")
    st.divider()
    
    # Actions
    st.subheader("Actions")
    if st.button("Back to Products", use_container_width=True):
        switch_page("app")
    
    st.divider()
    
    # User preferences
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

# Main content
st.markdown(f'<h1 class="main-header">{product["name"]}</h1>', unsafe_allow_html=True)

# Product details
with st.container():
    st.markdown('<div class="product-container">', unsafe_allow_html=True)
    
    # Product image and basic info
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Display image with error handling
        try:
            st.image(product['image_url'], width=300)
        except:
            st.image("streamlit/assets/default_meat.jpg", width=300)
    
    with col2:
        # Basic info
        st.subheader("Product Information")
        st.write(f"**Meat Type:** {product['meat_type']}")
        st.write(f"**Price:** ${product['price']:.2f}")
        
        # Description
        st.markdown(f"<div class='section-header'>Description</div>", unsafe_allow_html=True)
        st.write(product.get('description', 'No description available'))
        
        # Action buttons
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Add to Favorites", use_container_width=True, type="primary"):
                st.success("Added to favorites!")
        with col_b:
            if st.button("Share", use_container_width=True):
                st.info("Share link copied!")
    
    # Nutritional information
    st.markdown(f"<div class='section-header'>Nutritional Information</div>", unsafe_allow_html=True)
    
    # Display nutritional info in a responsive grid
    if 'nutrition' in product:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="nutrition-label">
                <div class="nutrition-header">Nutrition Facts</div>
                <div class="nutrition-item"><span>Calories</span><span>{calories}</span></div>
                <div class="nutrition-item"><span>Protein</span><span>{protein}</span></div>
                <div class="nutrition-item"><span>Fat</span><span>{fat}</span></div>
            </div>
            """.format(
                calories=product['nutrition'].get('calories', 'N/A'),
                protein=product['nutrition'].get('protein', 'N/A'),
                fat=product['nutrition'].get('fat', 'N/A')
            ), unsafe_allow_html=True)
        
        with col2:
            # Additional nutritional information could go here
            st.markdown("""
            <div class="nutrition-label">
                <div class="nutrition-header">Nutrition Details</div>
                <div class="nutrition-item"><span>Saturated Fat</span><span>--</span></div>
                <div class="nutrition-item"><span>Carbohydrates</span><span>--</span></div>
                <div class="nutrition-item"><span>Sodium</span><span>--</span></div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            # Additional nutritional information could go here
            st.markdown("""
            <div class="nutrition-label">
                <div class="nutrition-header">Health Metrics</div>
                <div class="nutrition-item"><span>Protein Quality</span><span>High</span></div>
                <div class="nutrition-item"><span>Preservatives</span><span>Low</span></div>
                <div class="nutrition-item"><span>Processing Level</span><span>Medium</span></div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Nutritional information not available")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Recommendations
st.markdown(f"<div class='section-header'>You Might Also Like</div>", unsafe_allow_html=True)

# Get recommendations
try:
    recommendations = get_recommendations()
    
    # Filter out the current product
    recommendations = [r for r in recommendations if r["id"] != product_id]
    
    # Display up to 3 recommendations
    if recommendations:
        cols = st.columns(3)
        
        for i, rec in enumerate(recommendations[:3]):
            with cols[i]:
                st.markdown(f"""
                <div class="recommendation-card">
                    <h4>{rec['name']}</h4>
                    <p>Type: {rec['meat_type']}</p>
                    <p>Price: ${rec['price']:.2f}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Display image with error handling
                try:
                    st.image(rec['image_url'], width=150)
                except:
                    st.image("streamlit/assets/default_meat.jpg", width=150)
                
                # View details button
                if st.button(f"View Details", key=f"rec_{rec['id']}"):
                    st.experimental_set_query_params(id=rec['id'])
                    st.experimental_rerun()
    else:
        st.info("No recommendations available")
        
except Exception as e:
    st.error(f"Failed to load recommendations: {str(e)}")

# Footer
st.markdown("""
<div style="text-align: center; margin-top: 3rem; color: #666;">
    <p>© 2023 MeatWise. All rights reserved.</p>
</div>
""", unsafe_allow_html=True) 