#!/usr/bin/env python3
"""
Clear-Meat API Startup Script
Handles environment switching and server startup with proper Python 3 support.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def activate_venv():
    """Activate virtual environment if available."""
    venv_path = Path(".venv")
    if venv_path.exists():
        # Update PATH to include venv binaries
        venv_bin = venv_path / "bin"
        os.environ["PATH"] = f"{venv_bin}:{os.environ['PATH']}"
        os.environ["VIRTUAL_ENV"] = str(venv_path.absolute())
        # Remove PYTHONHOME if set
        os.environ.pop("PYTHONHOME", None)
        print("✅ Virtual environment activated")
        return True
    return False

def switch_environment(env_name):
    """Switch to specified environment."""
    switch_script = Path("scripts/switch_env.py")
    if switch_script.exists():
        subprocess.run([sys.executable, str(switch_script), env_name], check=True)
        print(f"✅ Switched to {env_name} environment")
    else:
        print(f"⚠️  Environment switcher not found, using current environment")

def start_api(host="0.0.0.0", port=8000, reload=False):
    """Start the API server using uvicorn."""
    print("\n🚀 Starting Clear-Meat API...")
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", host,
        "--port", str(port)
    ]
    
    if reload:
        cmd.append("--reload")
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 API server stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start API: {e}")
        sys.exit(1)
    
def main():
    parser = argparse.ArgumentParser(description="Clear-Meat API Startup Script")
    parser.add_argument("--env", choices=["local", "production"], default="local",
                       help="Environment to use (default: local)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    # Activate virtual environment
    if not activate_venv():
        print("⚠️  No virtual environment found. Using system Python.")
    
    # Switch environment if needed
    if args.env:
        switch_environment(args.env)
    
    # Start the API
    start_api(args.host, args.port, args.reload)

if __name__ == "__main__":
    main() 