#!/usr/bin/env python3
"""
Environment Switcher Script

This script helps switch between development (local) and production environments
by modifying the .env file.
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

def main():
    """Main function to handle environment switching."""
    parser = argparse.ArgumentParser(description="Switch between development and production environments")
    parser.add_argument(
        "environment", 
        choices=["local", "production"], 
        help="Environment to switch to"
    )
    parser.add_argument(
        "--env-file", 
        default=".env", 
        help="Path to .env file (default: .env)"
    )
    
    args = parser.parse_args()
    
    # Get project root directory
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent
    env_templates_dir = script_dir / "env"
    
    # Define paths to environment template files
    env_templates = {
        "local": env_templates_dir / ".env.local",
        "backup": env_templates_dir / ".env.backup",
        "example": env_templates_dir / ".env.example"
    }
    
    # Load current .env file
    env_path = root_dir / args.env_file
    if not env_path.exists():
        print(f"Error: .env file not found at {env_path.absolute()}")
        print("Creating a new .env file...")
        env_path.touch()
    
    # Load existing variables
    current_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                current_vars[key.strip()] = value.strip()
    
    # Set environment variables based on selected environment
    if args.environment == "local":
        print("Switching to LOCAL development environment...")
        env_vars = {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql://postgres:postgres@localhost:54322/postgres",
            "SUPABASE_URL": current_vars.get("SUPABASE_URL", "http://localhost:54321"),
            "SUPABASE_KEY": current_vars.get("SUPABASE_KEY", "your-supabase-anon-key-here"),
            "DEBUG": "true"
        }
    else:  # production
        print("Switching to PRODUCTION environment...")
        # Keep existing production values if they exist
        env_vars = {
            "ENVIRONMENT": "production",
            "DATABASE_URL": current_vars.get("PRODUCTION_DATABASE_URL", ""),
            "SUPABASE_URL": current_vars.get("PRODUCTION_SUPABASE_URL", ""),
            "SUPABASE_KEY": current_vars.get("PRODUCTION_SUPABASE_KEY", ""),
            "DEBUG": "false"
        }
        
        # Check if production values are set
        if not env_vars["DATABASE_URL"] or not env_vars["SUPABASE_URL"] or not env_vars["SUPABASE_KEY"]:
            print("Warning: Some production variables are not set.")
            print("You should set PRODUCTION_DATABASE_URL, PRODUCTION_SUPABASE_URL, and PRODUCTION_SUPABASE_KEY")
            print("in your .env file to store production values.")
    
    # Update .env file with new values
    # First, preserve all existing variables
    all_vars = {**current_vars, **env_vars}
    
    # Write back to .env file
    with open(env_path, 'w') as f:
        f.write("# MeatWise Environment Configuration\n")
        f.write(f"# Active Environment: {args.environment.upper()}\n\n")
        
        # Write environment-specific variables first
        for key in ["ENVIRONMENT", "DATABASE_URL", "SUPABASE_URL", "SUPABASE_KEY", "DEBUG"]:
            if key in all_vars:
                f.write(f"{key}={all_vars[key]}\n")
        
        f.write("\n# Other variables\n")
        # Write all other variables
        for key, value in all_vars.items():
            if key not in ["ENVIRONMENT", "DATABASE_URL", "SUPABASE_URL", "SUPABASE_KEY", "DEBUG"]:
                f.write(f"{key}={value}\n")
    
    print(f"Environment switched to {args.environment.upper()}")
    print(f"Updated .env file at {env_path.absolute()}")
    print("\nTo apply these changes, restart your application:")
    print("./scripts/startup/start_local_dev.sh")

if __name__ == "__main__":
    main() 