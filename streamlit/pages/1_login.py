import streamlit as st
import requests
import json
from streamlit_extras.switch_page_button import switch_page
import extra_streamlit_components as stx

# Configuration
st.set_page_config(
    page_title="MeatWise - Login",
    page_icon="🥩",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4a4a4a;
        margin-bottom: 1rem;
        text-align: center;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #6b6b6b;
        margin-bottom: 2rem;
        text-align: center;
    }
    .auth-container {
        max-width: 500px;
        margin: 0 auto;
        padding: 2rem;
        background-color: #f9f9f9;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .divider {
        text-align: center;
        margin: 1.5rem 0;
        color: #666;
    }
    .centered {
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = False

if "user_data" not in st.session_state:
    st.session_state.user_data = {}

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "login"

if "onboarding_complete" not in st.session_state:
    st.session_state.onboarding_complete = False

# Check if already authenticated, redirect to main page if true
if st.session_state.user_authenticated:
    if st.session_state.onboarding_complete:
        switch_page("app")
    else:
        switch_page("onboarding")

# App header
st.markdown('<h1 class="main-header">MeatWise</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Your Personalized Meat Product Guide</p>', unsafe_allow_html=True)

# Tab selection
tab_choice = ["Login", "Register"]
tabs = stx.tab_bar(data=tab_choice, default=tab_choice[0 if st.session_state.active_tab == "login" else 1])

# Login form
if tabs == "Login":
    st.session_state.active_tab = "login"
    
    with st.container():
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        
        st.subheader("Welcome Back!")
        
        # Login form fields
        email = st.text_input("Email Address", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        # Error message placeholder
        login_error = st.empty()
        
        # Login button
        if st.button("Login", use_container_width=True):
            if not email or not password:
                login_error.error("Please fill in all fields")
            else:
                # Mock login API call
                # TODO: Replace with actual API call to your FastAPI backend
                try:
                    # Simulate API call
                    # In a real app, you would make a request to your backend
                    # response = requests.post(
                    #     "http://localhost:8001/api/v1/auth/login",
                    #     json={"email": email, "password": password}
                    # )
                    
                    # Mocking successful login for demo purposes
                    if email == "demo@example.com" and password == "password":
                        # Simulate successful login
                        st.session_state.user_authenticated = True
                        
                        # Mock user data that would normally come from the API
                        st.session_state.user_data = {
                            "id": 1,
                            "name": "Demo User",
                            "email": email,
                            "preferences": {
                                "dietary_preferences": [],
                                "cooking_experience": "",
                                "meat_preferences": []
                            }
                        }
                        
                        # Check if user has completed onboarding
                        has_preferences = bool(st.session_state.user_data.get("preferences", {}).get("meat_preferences"))
                        st.session_state.onboarding_complete = has_preferences
                        
                        # Redirect based on onboarding status
                        if st.session_state.onboarding_complete:
                            switch_page("app")
                        else:
                            switch_page("onboarding")
                    else:
                        login_error.error("Invalid email or password")
                
                except Exception as e:
                    login_error.error(f"Login failed: {str(e)}")
        
        # Forgot password link
        st.markdown('<div class="centered">', unsafe_allow_html=True)
        st.markdown("[Forgot Password?](#)")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# Registration form
elif tabs == "Register":
    st.session_state.active_tab = "register"
    
    with st.container():
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        
        st.subheader("Create an Account")
        
        # Registration form fields
        name = st.text_input("Full Name", key="reg_name")
        email = st.text_input("Email Address", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")
        
        # Error message placeholder
        register_error = st.empty()
        
        # Register button
        if st.button("Register", use_container_width=True):
            # Form validation
            if not name or not email or not password or not confirm_password:
                register_error.error("Please fill in all fields")
            elif password != confirm_password:
                register_error.error("Passwords do not match")
            else:
                # Mock registration API call
                # TODO: Replace with actual API call to your FastAPI backend
                try:
                    # Simulate API call
                    # In a real app, you would make a request to your backend
                    # response = requests.post(
                    #     "http://localhost:8001/api/v1/auth/register",
                    #     json={"name": name, "email": email, "password": password}
                    # )
                    
                    # Mocking successful registration for demo purposes
                    # Simulate successful registration
                    st.session_state.user_authenticated = True
                    
                    # Mock user data that would normally come from the API
                    st.session_state.user_data = {
                        "id": 1,
                        "name": name,
                        "email": email,
                        "preferences": {
                            "dietary_preferences": [],
                            "cooking_experience": "",
                            "meat_preferences": []
                        }
                    }
                    
                    # New users need to complete onboarding
                    st.session_state.onboarding_complete = False
                    
                    # Redirect to onboarding
                    switch_page("onboarding")
                
                except Exception as e:
                    register_error.error(f"Registration failed: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
<div style="text-align: center; margin-top: 3rem; color: #666;">
    <p>© 2023 MeatWise. All rights reserved.</p>
</div>
""", unsafe_allow_html=True) 