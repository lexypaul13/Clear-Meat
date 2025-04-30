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
    .option-reason {
        font-size: 0.8rem;
        color: #6b6b6b;
        font-style: italic;
        margin-top: 0.25rem;
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

# New preference fields based on updated structure
if "nutrition_focus" not in st.session_state:
    st.session_state.nutrition_focus = None

if "avoid_preservatives" not in st.session_state:
    st.session_state.avoid_preservatives = None

if "prefer_antibiotic_free" not in st.session_state:
    st.session_state.prefer_antibiotic_free = None

if "prefer_grass_fed" not in st.session_state:
    st.session_state.prefer_grass_fed = None

if "cooking_style" not in st.session_state:
    st.session_state.cooking_style = None
    
if "open_to_alternatives" not in st.session_state:
    st.session_state.open_to_alternatives = None

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
for i in range(1, 8):  # Increased to 7 steps (welcome + 6 questions)
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
    
    # Step 2: Nutrition Priorities (Screen 1)
    elif st.session_state.onboarding_step == 2:
        st.subheader("What's your main nutrition focus when choosing meat?")
        
        # Options with descriptions
        options = [
            ("protein", "Getting more protein", "Looking to build or maintain muscle"),
            ("fat", "Cutting back on fat", "Choosing lean cuts for less saturated fat"),
            ("salt", "Watching my salt intake", "Avoiding high sodium for heart health")
        ]
        
        # Display options as selectable cards
        for value, label, description in options:
            is_selected = st.session_state.nutrition_focus == value
            col = st.container()
            
            if col.button(
                label,
                key=f"nutrition_{value}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.nutrition_focus = value
            
            st.markdown(f'<div class="option-reason">({description})</div>', unsafe_allow_html=True)
            st.write("")  # Add some spacing
        
        # Why this question matters
        with st.expander("Why does this matter?"):
            st.write("""
            Nutrition goals vary: in fitness circles, hitting protein targets is key, whereas health experts warn that 
            processed meats are often high in saturated fat and salt, raising cardiovascular risks. This question lets 
            you tell the app if you're mainly about protein, or if you're trying to limit fat or salt.
            """)
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.onboarding_step = 1
                st.experimental_rerun()
        with col2:
            next_disabled = st.session_state.nutrition_focus is None
            if st.button("Next", use_container_width=True, disabled=next_disabled):
                st.session_state.onboarding_step = 3
                st.experimental_rerun()
            
            if next_disabled:
                st.info("Please select a nutrition focus to continue")
    
    # Step 3: Additives and Preservatives (Screen 2)
    elif st.session_state.onboarding_step == 3:
        st.subheader("Do you try to avoid preservatives in your meat (e.g. nitrites in bacon)?")
        
        # Options with descriptions
        options = [
            (True, "Yes, I avoid those", "I go for 'nitrite-free'/uncured products"),
            (False, "No, not really", "I'm not too worried about that")
        ]
        
        # Display options as selectable buttons
        for value, label, description in options:
            is_selected = st.session_state.avoid_preservatives == value
            col = st.container()
            
            if col.button(
                label,
                key=f"preservatives_{value}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.avoid_preservatives = value
            
            st.markdown(f'<div class="option-reason">({description})</div>', unsafe_allow_html=True)
            st.write("")  # Add some spacing
        
        # Why this question matters
        with st.expander("Why does this matter?"):
            st.write("""
            Clean-eating advocates often caution against additives like sodium nitrite used in cured meats. 
            Experts note that nitrites can form carcinogenic compounds when cooked, and processed meats with 
            these additives have been linked to higher cancer risk. If you're the type to check for "no added nitrates/nitrites" 
            on labels, the app will note it. (If not, no worries — it's okay either way!)
            """)
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.onboarding_step = 2
                st.experimental_rerun()
        with col2:
            next_disabled = st.session_state.avoid_preservatives is None
            if st.button("Next", use_container_width=True, disabled=next_disabled):
                st.session_state.onboarding_step = 4
                st.experimental_rerun()
            
            if next_disabled:
                st.info("Please select an option to continue")
    
    # Step 4: Antibiotics and Hormones (Screen 3)
    elif st.session_state.onboarding_step == 4:
        st.subheader("Do you prefer meat from animals raised without antibiotics or hormones?")
        
        # Options with descriptions
        options = [
            (True, "Yes, that's important to me", "I look for antibiotic-free labels"),
            (False, "No, I'm not concerned", "Regular meat is fine by me")
        ]
        
        # Display options as selectable buttons
        for value, label, description in options:
            is_selected = st.session_state.prefer_antibiotic_free == value
            col = st.container()
            
            if col.button(
                label,
                key=f"antibiotics_{value}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.prefer_antibiotic_free = value
            
            st.markdown(f'<div class="option-reason">({description})</div>', unsafe_allow_html=True)
            st.write("")  # Add some spacing
        
        # Why this question matters
        with st.expander("Why does this matter?"):
            st.write("""
            Many North American consumers now seek out "raised without antibiotics" (and hormone-free) meat 
            for health and ethical reasons. In fact, demand for antibiotic-free beef is surging alongside 
            grass-fed options. Parents and millennials especially want transparency about how their meat was raised. 
            This question lets you indicate if these farming practices matter to you.
            """)
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.onboarding_step = 3
                st.experimental_rerun()
        with col2:
            next_disabled = st.session_state.prefer_antibiotic_free is None
            if st.button("Next", use_container_width=True, disabled=next_disabled):
                st.session_state.onboarding_step = 5
                st.experimental_rerun()
            
            if next_disabled:
                st.info("Please select an option to continue")
    
    # Step 5: Sourcing & Animal Diet (Screen 4)
    elif st.session_state.onboarding_step == 5:
        st.subheader("Do you look for grass-fed or pasture-raised meat options?")
        
        # Options with descriptions
        options = [
            (True, "Yes, I prefer those", "Grass-fed beef, pasture-raised poultry, etc."),
            (False, "No, not really", "I don't specifically seek that out")
        ]
        
        # Display options as selectable buttons
        for value, label, description in options:
            is_selected = st.session_state.prefer_grass_fed == value
            col = st.container()
            
            if col.button(
                label,
                key=f"grass_fed_{value}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.prefer_grass_fed = value
            
            st.markdown(f'<div class="option-reason">({description})</div>', unsafe_allow_html=True)
            st.write("")  # Add some spacing
        
        # Why this question matters
        with st.expander("Why does this matter?"):
            st.write("""
            "Grass-fed" and "pasture-raised" are growing buzzwords. Nearly 65% of shoppers like to know where their 
            food comes from, and producers have seen grass-fed meat sales jump ~30% amid this trend. Grass-fed beef, 
            for example, is often seen as more natural or humane. By telling us if these labels matter to you, ClearCut AI 
            can highlight products that meet your standards (or just show you everything if you have no preference).
            """)
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.onboarding_step = 4
                st.experimental_rerun()
        with col2:
            next_disabled = st.session_state.prefer_grass_fed is None
            if st.button("Next", use_container_width=True, disabled=next_disabled):
                st.session_state.onboarding_step = 6
                st.experimental_rerun()
            
            if next_disabled:
                st.info("Please select an option to continue")
    
    # Step 6: Typical Cooking Style (Screen 5)
    elif st.session_state.onboarding_step == 6:
        st.subheader("How do you usually cook your meat?")
        
        # Options with descriptions
        options = [
            ("grilling", "Grilling/BBQ", "I love firing up the grill"),
            ("pan_frying", "Pan-frying on the stove", "Quick sear or sauté on a stovetop pan"),
            ("oven_slow_cooker", "Oven or slow cooker", "Baking, roasting, or slow-cooking meals")
        ]
        
        # Display options as selectable buttons
        for value, label, description in options:
            is_selected = st.session_state.cooking_style == value
            col = st.container()
            
            if col.button(
                label,
                key=f"cooking_{value}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.cooking_style = value
            
            st.markdown(f'<div class="option-reason">({description})</div>', unsafe_allow_html=True)
            st.write("")  # Add some spacing
        
        # Why this question matters
        with st.expander("Why does this matter?"):
            st.write("""
            Everyone's kitchen style is a bit different! Maybe you're a BBQ master, or perhaps you prefer one-pan 
            meals on the stove. (Some folks toss things in a slow cooker or oven and let it go.) This question helps 
            the app give you relevant cooking tips and recipe ideas. For instance, if you mostly grill, we might share 
            grilling safety tips or marinade suggestions. (Fun fact: Grilling is super popular – about 89% of people 
            in one survey grill their steaks at home!)
            """)
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.onboarding_step = 5
                st.experimental_rerun()
        with col2:
            next_disabled = st.session_state.cooking_style is None
            if st.button("Next", use_container_width=True, disabled=next_disabled):
                st.session_state.onboarding_step = 7
                st.experimental_rerun()
            
            if next_disabled:
                st.info("Please select a cooking style to continue")
    
    # Step 7: Openness to Meat Alternatives (Screen 6)
    elif st.session_state.onboarding_step == 7:
        st.subheader("Are you open to trying plant-based meat alternatives?")
        
        # Options with descriptions
        options = [
            (True, "Yes, I'd try them", "Open to options like Beyond™ or Impossible™ meats"),
            (False, "No, I prefer real meat", "Stick with traditional meat only")
        ]
        
        # Display options as selectable buttons
        for value, label, description in options:
            is_selected = st.session_state.open_to_alternatives == value
            col = st.container()
            
            if col.button(
                label,
                key=f"alternatives_{value}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.open_to_alternatives = value
            
            st.markdown(f'<div class="option-reason">({description})</div>', unsafe_allow_html=True)
            st.write("")  # Add some spacing
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.onboarding_step = 6
                st.experimental_rerun()
        with col2:
            complete_disabled = st.session_state.open_to_alternatives is None
            if st.button("Complete", use_container_width=True, disabled=complete_disabled):
                # Save preferences to user data
                if "preferences" not in st.session_state.user_data:
                    st.session_state.user_data["preferences"] = {}
                
                # Save new preferences format
                st.session_state.user_data["preferences"]["nutrition_focus"] = st.session_state.nutrition_focus
                st.session_state.user_data["preferences"]["avoid_preservatives"] = st.session_state.avoid_preservatives
                st.session_state.user_data["preferences"]["prefer_antibiotic_free"] = st.session_state.prefer_antibiotic_free
                st.session_state.user_data["preferences"]["prefer_grass_fed"] = st.session_state.prefer_grass_fed
                st.session_state.user_data["preferences"]["cooking_style"] = st.session_state.cooking_style
                st.session_state.user_data["preferences"]["open_to_alternatives"] = st.session_state.open_to_alternatives
                
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
                st.info("Please select an option to continue")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
<div style="text-align: center; margin-top: 3rem; color: #666;">
    <p>© 2023 MeatWise. All rights reserved.</p>
</div>
""", unsafe_allow_html=True) 