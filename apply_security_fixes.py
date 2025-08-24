#!/usr/bin/env python3
"""
Apply security fixes to Supabase database
"""

import os
from app.db.supabase_client import get_admin_supabase

def apply_security_fixes():
    """Apply the function search path security fixes."""
    
    print("🔐 Applying security fixes to Supabase database...")
    
    # Get admin client
    admin_client = get_admin_supabase()
    if not admin_client:
        print("❌ Failed to connect to Supabase")
        return False
    
    # Read the migration SQL
    migration_file = '/Users/alexpaul/Desktop/Clear-Meat/supabase/migrations/20250730_fix_function_search_paths.sql'
    with open(migration_file, 'r') as f:
        sql_content = f.read()
    
    # Split into individual statements (crude but effective for this case)
    statements = sql_content.split(';\n')
    
    success_count = 0
    error_count = 0
    
    for i, statement in enumerate(statements, 1):
        statement = statement.strip()
        if not statement or statement.startswith('--'):
            continue
            
        # Add semicolon back
        if not statement.endswith(';'):
            statement += ';'
        
        try:
            # Execute using RPC (raw SQL execution)
            print(f"  Executing statement {i}...")
            # Use postgrest client's raw SQL execution
            result = admin_client.rpc('exec_sql', {'sql': statement}).execute()
            print(f"  ✅ Statement {i} executed successfully")
            success_count += 1
        except Exception as e:
            # Try alternate approach - direct execution
            try:
                # Some statements might not work via RPC, skip them
                if 'CREATE OR REPLACE FUNCTION' in statement:
                    print(f"  ⚠️  Statement {i} needs to be run directly in Supabase SQL Editor")
                else:
                    print(f"  ❌ Statement {i} failed: {str(e)}")
                error_count += 1
            except:
                pass
    
    print(f"\n📊 Results:")
    print(f"  ✅ Successful: {success_count}")
    print(f"  ❌ Failed: {error_count}")
    
    if error_count > 0:
        print("\n⚠️  Some statements failed. You may need to:")
        print("  1. Go to Supabase SQL Editor: https://supabase.com/dashboard/project/ksgxendfsejkxhrmfsbi/sql")
        print("  2. Copy the contents of supabase/migrations/20250730_fix_function_search_paths.sql")
        print("  3. Paste and run in the SQL Editor")
    
    return success_count > 0

if __name__ == "__main__":
    apply_security_fixes()