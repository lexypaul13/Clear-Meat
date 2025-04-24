#!/usr/bin/env python3
"""
MeatWise Streamlit App Launcher

This script provides a convenient way to start the MeatWise Streamlit app.
It handles checking if all required packages are installed and starting the app.
"""
import os
import sys
import subprocess
import importlib.util

def check_package(package_name):
    """Check if a package is installed."""
    return importlib.util.find_spec(package_name) is not None

def install_requirements():
    """Install required packages from requirements.txt."""
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("Package installation complete!")

def main():
    """Main function to run the app."""
    # Check if Streamlit is installed
    if not check_package("streamlit"):
        print("Streamlit is not installed. Installing requirements...")
        install_requirements()
    
    # Generate default meat images if they don't exist
    default_image_path = "streamlit/assets/default_meat.jpg"
    if not os.path.exists(default_image_path):
        print("Generating default meat images...")
        image_utils_path = os.path.join("streamlit", "utils", "image_utils.py")
        if os.path.exists(image_utils_path):
            subprocess.check_call([sys.executable, image_utils_path])
    
    # Run the Streamlit app
    print("Starting MeatWise Streamlit app...")
    streamlit_path = os.path.join("streamlit", "app.py")
    
    try:
        # Use subprocess.Popen instead of check_call for better compatibility
        # This is the correct way to run a Streamlit app programmatically
        cmd = [sys.executable, "-m", "streamlit", "run", streamlit_path]
        print(f"Running command: {' '.join(cmd)}")
        process = subprocess.Popen(cmd)
        process.wait()
    except Exception as e:
        print(f"Error starting Streamlit: {e}")
        print("\nAlternative: Run the app directly with:")
        print(f"streamlit run {streamlit_path}")

if __name__ == "__main__":
    main() 