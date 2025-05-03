#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys

def clean_repo():
    """
    Clean up the repository by removing temporary files, logs, and caches.
    """
    print("Starting repository cleanup...")
    
    # Define files and directories to remove
    log_files = [
        'server.log', 'server_log.txt', 'image_verification.log', 'bulk_import.log',
        'image_updater.log', 'image_analysis.log', 'real_import.log', 
        'mock_data_cleanup.log', 'data_purge.log', 'meat_product_import.log'
    ]
    
    temp_files = [
        'token.json', 'token_new.json', 'token2.json', 'token3.json',
        'add_test_product.py', 'test_gemini_directly.py', 'test_gemini_service.py',
        'test_connection.py', 'check_product.py'
    ]
    
    cache_dirs = [
        '__pycache__', '.pytest_cache'
    ]
    
    # Remove log files
    print("Removing log files...")
    for log_file in log_files:
        if os.path.exists(log_file):
            os.remove(log_file)
            print(f"  Removed {log_file}")
    
    # Remove temporary files
    print("Removing temporary files...")
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)
            print(f"  Removed {temp_file}")
    
    # Clean up Python cache files and directories
    print("Cleaning Python cache files...")
    for root, dirs, files in os.walk('.'):
        # Skip virtual environments
        if 'venv' in root or '.venv' in root or 'node_modules' in root:
            continue
            
        # Remove cache directories
        for cache_dir in cache_dirs:
            if cache_dir in dirs:
                path = os.path.join(root, cache_dir)
                shutil.rmtree(path)
                print(f"  Removed {path}")
        
        # Remove .pyc files
        for file in files:
            if file.endswith('.pyc'):
                path = os.path.join(root, file)
                os.remove(path)
                print(f"  Removed {path}")
    
    print("Repository cleaned successfully!")

def check_and_commit():
    """
    Check git status and commit changes if desired.
    """
    try:
        # Check if git is installed
        subprocess.run(['git', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Check git status
        status = subprocess.run(['git', 'status'], check=True, stdout=subprocess.PIPE).stdout.decode('utf-8')
        print("\nGit Status:")
        print(status)
        
        # Ask if user wants to commit changes
        response = input("\nDo you want to commit these changes? (y/n): ").strip().lower()
        if response == 'y':
            message = input("Enter commit message: ").strip()
            if not message:
                message = "Clean up repository for deployment"
            
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run(['git', 'commit', '-m', message], check=True)
            print("Changes committed successfully!")
            
            # Ask if user wants to push changes
            push = input("Do you want to push these changes? (y/n): ").strip().lower()
            if push == 'y':
                subprocess.run(['git', 'push'], check=True)
                print("Changes pushed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {e}")
    except FileNotFoundError:
        print("Git is not installed or not in PATH.")

if __name__ == "__main__":
    clean_repo()
    check_and_commit() 