import streamlit as st
import os

def product_card(product, on_click=None, key_prefix=""):
    """
    Render a product card component
    
    Parameters:
    - product: Dict containing product data
    - on_click: Optional callback function when View Details is clicked
    - key_prefix: Prefix for component keys to ensure uniqueness
    
    Returns:
    - clicked: Boolean indicating if the details button was clicked
    """
    with st.container():
        # Product card with styling
        st.markdown(f"""
        <div style="
            background-color: #f9f9f9;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 15px;
        ">
            <h3 style="margin-top: 0;">{product['name']}</h3>
            <p><strong>Type:</strong> {product['meat_type']}</p>
            <p><strong>Price:</strong> ${product['price']:.2f}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Product image
        try:
            st.image(product['image_url'], width=200)
        except:
            # Try to use a meat-type specific image
            meat_type_img = f"streamlit/assets/meat_types/{product['meat_type'].lower().replace(' ', '_')}.jpg"
            if os.path.exists(meat_type_img):
                st.image(meat_type_img, width=200)
            else:
                st.image("streamlit/assets/default_meat.jpg", width=200)
        
        # Nutritional info preview
        if 'nutrition' in product:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Protein:** {product['nutrition']['protein']}")
            with col2:
                st.write(f"**Fat:** {product['nutrition']['fat']}")
            with col3:
                st.write(f"**Cal:** {product['nutrition']['calories']}")
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            details_clicked = st.button(
                "View Details", 
                key=f"{key_prefix}_view_{product['id']}",
                use_container_width=True
            )
            if details_clicked and on_click:
                on_click(product['id'])
        
        with col2:
            fav_clicked = st.button(
                "❤️", 
                key=f"{key_prefix}_fav_{product['id']}",
                use_container_width=True
            )
            if fav_clicked:
                st.success("Added to favorites!")
        
        return details_clicked

def product_grid(products, columns=3, on_product_click=None):
    """
    Render a grid of product cards
    
    Parameters:
    - products: List of product dictionaries
    - columns: Number of columns in the grid
    - on_product_click: Callback function when a product is clicked
    
    Returns:
    - clicked_product_id: ID of the clicked product, or None if none clicked
    """
    if not products:
        st.info("No products to display")
        return None
    
    # Create columns
    cols = st.columns(columns)
    clicked_product_id = None
    
    # Populate grid
    for i, product in enumerate(products):
        with cols[i % columns]:
            clicked = product_card(
                product,
                on_click=on_product_click,
                key_prefix=f"grid_{i}"
            )
            if clicked and on_product_click is None:
                clicked_product_id = product['id']
    
    return clicked_product_id 