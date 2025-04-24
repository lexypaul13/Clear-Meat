import streamlit as st
from streamlit_extras.switch_page_button import switch_page

# Configuration
st.set_page_config(
    page_title="MeatWise - Onboarding",
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
    .onboarding-container {
        max-width: 700px;
        margin: 0 auto;
        padding: 2rem;
        background-color: #f9f9f9;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .navigation-buttons {
        display: flex;
        justify-content: space-between;
        margin-top: 2rem;
    }
    .centered {
        text-align: center;
    }
    .option-card {
        padding: 1rem;
        border-radius: 8px;
        background-color: #f0f0f0;
        margin-bottom: 1rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .option-card:hover {
        background-color: #e0e0e0;
    }
    .option-card.selected {
        background-color: #FF4B4B;
        color: white;
    }
    .progress-container {
        margin-bottom: 2rem;
    }
    .progress-step {
        display: inline-block;
        width: 10px;
        height: 10px;
        margin: 0 5px;
        border-radius: 50%;
        background-color: #ddd;
    }
    .progress-step.active {
        background-color: #FF4B4B;
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

if "onboarding_step" not in st.session_state:
    st.session_state.onboarding_step = 1

if "dietary_preferences" not in st.session_state:
    st.session_state.dietary_preferences = []

if "cooking_experience" not in st.session_state:
    st.session_state.cooking_experience = ""

if "meat_preferences" not in st.session_state:
    st.session_state.meat_preferences = []

# Check if user is not authenticated, redirect to login
if not st.session_state.user_authenticated:
    switch_page("login")

# Check if onboarding is already complete, redirect to main page
if st.session_state.onboarding_complete:
    switch_page("app")

# App header
st.markdown('<h1 class="main-header">MeatWise Onboarding</h1>', unsafe_allow_html=True)

# Progress bar
progress_html = '<div class="progress-container centered">'
for i in range(1, 5):
    if i <= st.session_state.onboarding_step:
        progress_html += f'<span class="progress-step active"></span>'
    else:
        progress_html += f'<span class="progress-step"></span>'
progress_html += '</div>'
st.markdown(progress_html, unsafe_allow_html=True)

# Onboarding container
with st.container():
    st.markdown('<div class="onboarding-container">', unsafe_allow_html=True)
    
    # Step 1: Welcome Screen
    if st.session_state.onboarding_step == 1:
        st.subheader("Welcome to MeatWise!")
        st.write("MeatWise helps you discover meat products tailored to your preferences and needs.")
        st.write("We'll guide you through a quick onboarding process to personalize your experience.")
        
        # Show user's name if available
        if st.session_state.user_data.get("name"):
            st.write(f"Hi {st.session_state.user_data.get('name')}! Let's get started.")
        
        # Next button
        if st.button("Get Started", use_container_width=True):
            st.session_state.onboarding_step = 2
            st.experimental_rerun()
    
    # Step 2: Dietary Preferences
    elif st.session_state.onboarding_step == 2:
        st.subheader("What are your dietary preferences?")
        st.write("Select any dietary restrictions or preferences that apply to you.")
        
        # Dietary preferences options
        dietary_options = [
            "Vegetarian", "Vegan", "Halal", "Kosher", "Gluten-Free", 
            "Dairy-Free", "Low Sodium", "Low Carb", "No Artificial Ingredients"
        ]
        
        # Display options in a grid
        col1, col2 = st.columns(2)
        
        for i, option in enumerate(dietary_options):
            with col1 if i % 2 == 0 else col2:
                is_selected = option in st.session_state.dietary_preferences
                if st.checkbox(option, value=is_selected, key=f"diet_{option}"):
                    if option not in st.session_state.dietary_preferences:
                        st.session_state.dietary_preferences.append(option)
                else:
                    if option in st.session_state.dietary_preferences:
                        st.session_state.dietary_preferences.remove(option)
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.onboarding_step = 1
                st.experimental_rerun()
        with col2:
            if st.button("Next", use_container_width=True):
                st.session_state.onboarding_step = 3
                st.experimental_rerun()
    
    # Step 3: Cooking Experience
    elif st.session_state.onboarding_step == 3:
        st.subheader("How would you describe your cooking experience?")
        st.write("This helps us recommend products that match your cooking skill level.")
        
        # Cooking experience options
        experience_options = ["Beginner", "Intermediate", "Expert"]
        
        # Display options as selectable cards
        for option in experience_options:
            is_selected = st.session_state.cooking_experience == option
            col = st.container()
            
            if col.button(
                option,
                key=f"exp_{option}",
                help=f"Select if you're a {option.lower()} cook",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.cooking_experience = option
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.onboarding_step = 2
                st.experimental_rerun()
        with col2:
            next_disabled = not st.session_state.cooking_experience
            if st.button("Next", use_container_width=True, disabled=next_disabled):
                st.session_state.onboarding_step = 4
                st.experimental_rerun()
            
            if next_disabled:
                st.info("Please select your cooking experience level to continue")
    
    # Step 4: Meat Preferences
    elif st.session_state.onboarding_step == 4:
        st.subheader("Which types of meat do you prefer?")
        st.write("Select all meat types that you're interested in.")
        
        # Meat preferences options
        meat_options = ["Beef", "Pork", "Poultry", "Lamb", "Fish", "Venison", "Duck", "Turkey", "Other"]
        
        # Display options in a grid
        cols = st.columns(3)
        
        for i, option in enumerate(meat_options):
            with cols[i % 3]:
                is_selected = option in st.session_state.meat_preferences
                if st.checkbox(option, value=is_selected, key=f"meat_{option}"):
                    if option not in st.session_state.meat_preferences:
                        st.session_state.meat_preferences.append(option)
                else:
                    if option in st.session_state.meat_preferences:
                        st.session_state.meat_preferences.remove(option)
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.onboarding_step = 3
                st.experimental_rerun()
        with col2:
            complete_disabled = len(st.session_state.meat_preferences) == 0
            if st.button("Complete", use_container_width=True, disabled=complete_disabled):
                # Save preferences to user data
                if "preferences" not in st.session_state.user_data:
                    st.session_state.user_data["preferences"] = {}
                
                st.session_state.user_data["preferences"]["dietary_preferences"] = st.session_state.dietary_preferences
                st.session_state.user_data["preferences"]["cooking_experience"] = st.session_state.cooking_experience
                st.session_state.user_data["preferences"]["meat_preferences"] = st.session_state.meat_preferences
                
                # Mark onboarding as complete
                st.session_state.onboarding_complete = True
                
                # TODO: In a real application, make API call to save preferences
                # try:
                #     response = requests.post(
                #         "http://localhost:8001/api/v1/users/preferences",
                #         json=st.session_state.user_data["preferences"],
                #         headers={"Authorization": f"Bearer {st.session_state.user_data.get('token')}"}
                #     )
                # except Exception as e:
                #     st.error(f"Failed to save preferences: {str(e)}")
                
                # Redirect to main app
                switch_page("app")
            
            if complete_disabled:
                st.info("Please select at least one meat preference to continue")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
<div style="text-align: center; margin-top: 3rem; color: #666;">
    <p>© 2023 MeatWise. All rights reserved.</p>
</div>
""", unsafe_allow_html=True) 