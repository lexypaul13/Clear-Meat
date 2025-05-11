#!/usr/bin/env python3
"""
MeatWise API Starter Script Wrapper

This script serves as a wrapper that calls the main starter script in scripts/startup/.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Call the main starter script in scripts/startup/."""
    script_path = Path(__file__).parent / "scripts" / "startup" / "start_app.py"
    
    if not script_path.exists():
        print(f"Error: Starter script not found at {script_path}")
        sys.exit(1)
    
    print(f"Calling starter script at {script_path}...")
    
    # Pass all arguments to the actual script
    args = [sys.executable, str(script_path)] + sys.argv[1:]
    subprocess.run(args)

if __name__ == "__main__":
    main() 