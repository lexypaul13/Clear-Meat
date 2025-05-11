#!/usr/bin/env python3
"""
MeatWise API Starter Script

This script starts the MeatWise API with proper environment configuration.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to path
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent
sys.path.append(str(root_dir))

def main():
    """Main function to start the MeatWise API."""
    parser = argparse.ArgumentParser(description="Start the MeatWise API with environment configuration")
    parser.add_argument(
        "--env", 
        choices=["local", "production"], 
        default="local",
        help="Environment to use (default: local)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8001,
        help="Port to run the API on (default: 8001)"
    )
    parser.add_argument(
        "--reload", 
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    args = parser.parse_args()
    
    # Switch environment if requested
    if args.env:
        print(f"Setting up {args.env} environment...")
        env_script = root_dir / "scripts" / "switch_env.py"
        subprocess.run([sys.executable, str(env_script), args.env], check=True)
    
    # Start the API
    reload_flag = "--reload" if args.reload else ""
    cmd = f"uvicorn app.main:app --host 0.0.0.0 --port {args.port} {reload_flag}"
    
    print(f"Starting MeatWise API on port {args.port} in {args.env} environment...")
    print(f"Running command: {cmd}")
    
    # Change to the root directory before executing
    os.chdir(str(root_dir))
    
    # Execute the command
    os.system(cmd)

if __name__ == "__main__":
    main() 