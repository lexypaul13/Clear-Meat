#!/usr/bin/env python3
"""
Check for exposed credentials in the codebase.
This script helps prevent accidental exposure of sensitive information.
"""

import os
import re
import logging
from typing import List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Patterns to look for
PATTERNS = [
    (r'postgresql://[^@]+:[^@]+@[^/]+', 'Database URL'),
    (r'supabase\.szswmlkhirkmozwvhpnc', 'Supabase Project ID'),
    (r'key=[A-Za-z0-9._-]+', 'API Key'),
    (r'secret=[A-Za-z0-9._-]+', 'Secret Key'),
    (r'password=[A-Za-z0-9._-]+', 'Password'),
    (r'token=[A-Za-z0-9._-]+', 'Token')
]

def should_check_file(filepath: str) -> bool:
    """Determine if a file should be checked for credentials."""
    # Skip binary files, images, etc.
    binary_extensions = {'.pyc', '.pyo', '.so', '.dll', '.jpg', '.png', '.gif'}
    # Skip version control directories
    skip_dirs = {'.git', '.svn', 'node_modules', 'venv', 'env'}
    
    # Check file extension
    _, ext = os.path.splitext(filepath)
    if ext in binary_extensions:
        return False
        
    # Check directory path
    parts = filepath.split(os.sep)
    if any(part in skip_dirs for part in parts):
        return False
        
    return True

def scan_file(filepath: str) -> List[Tuple[str, int, str, str]]:
    """Scan a file for potential credentials."""
    findings = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                for pattern, desc in PATTERNS:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        # Skip if it's in a comment
                        if '#' in line[:match.start()] or '//' in line[:match.start()]:
                            continue
                        findings.append((
                            filepath,
                            i,
                            desc,
                            match.group()
                        ))
    except Exception as e:
        logger.warning(f"Could not scan {filepath}: {str(e)}")
    
    return findings

def main():
    logger.info("Starting credential scan...")
    
    total_files = 0
    total_findings = 0
    
    # Walk through all files in the current directory
    for root, _, files in os.walk('.'):
        for file in files:
            filepath = os.path.join(root, file)
            
            if not should_check_file(filepath):
                continue
                
            total_files += 1
            findings = scan_file(filepath)
            
            if findings:
                total_findings += len(findings)
                print(f"\nPotential credentials found in {filepath}:")
                print("-" * 80)
                for file, line, desc, match in findings:
                    print(f"Line {line}: {desc}")
                    print(f"Found: {match}")
                    print("-" * 80)
    
    print(f"\nScan complete!")
    print(f"Files scanned: {total_files}")
    print(f"Potential credentials found: {total_findings}")
    
    if total_findings > 0:
        print("\nPlease review these findings and ensure no sensitive data is exposed.")
        print("Consider moving credentials to environment variables in a .env file.")
        exit(1)

if __name__ == "__main__":
    main() 