import os
import shutil
from pathlib import Path

# Files to move to scripts directory
files_to_move = [
    'test_gemini_directly.py',
    'test_gemini_service.py',
    'add_test_product.py',
    'check_db_schemas.py',
]

# Log files to delete
log_files = [
    'image_verification.log',
    'bulk_import.log',
    'meat_product_import.log',
]

def main():
    # Create a 'debug' subdirectory in scripts if it doesn't exist
    scripts_debug_dir = Path('scripts/debug')
    scripts_debug_dir.mkdir(exist_ok=True)
    
    # Move files to scripts/debug directory
    for file_name in files_to_move:
        if os.path.exists(file_name):
            print(f"Moving {file_name} to scripts/debug/")
            shutil.move(file_name, scripts_debug_dir / file_name)
        else:
            print(f"File {file_name} not found")
    
    # Delete log files
    for log_file in log_files:
        if os.path.exists(log_file):
            print(f"Removing log file: {log_file}")
            os.remove(log_file)
        else:
            print(f"Log file {log_file} not found")
    
    print("Cleanup complete!")

if __name__ == "__main__":
    main() 