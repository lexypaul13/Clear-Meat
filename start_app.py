#!/usr/bin/env python3
"""
Simple script to start the Streamlit app directly
"""
import os
import subprocess
import sys

def main():
    """Run the Streamlit app directly"""
    streamlit_path = os.path.join("streamlit", "app.py")
    
    print(f"Starting MeatWise Streamlit app from {streamlit_path}...")
    
    # Command to run the Streamlit app
    cmd = ["streamlit", "run", streamlit_path]
    
    try:
        # Try running the command directly
        subprocess.run(cmd, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\nError running Streamlit. Trying with python -m...")
        try:
            # Try using python -m streamlit
            subprocess.run([sys.executable, "-m", "streamlit", "run", streamlit_path], check=True)
        except Exception as e:
            print(f"\nError: {e}")
            print("\nPlease make sure Streamlit is installed:")
            print("pip install streamlit streamlit-extras extra-streamlit-components")
            print("\nThen run:")
            print(f"streamlit run {streamlit_path}")

if __name__ == "__main__":
    main() 