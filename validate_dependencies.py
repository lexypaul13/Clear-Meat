#!/usr/bin/env python3
"""
Dependency validation script for Railway deployment.
Tests critical imports to ensure compatibility.
"""

import sys
import importlib.util

def test_import(module_name, description):
    """Test if a module can be imported successfully."""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            print(f"❌ {description}: Module '{module_name}' not found")
            return False
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"✅ {description}: {module_name}")
        return True
    except Exception as e:
        print(f"❌ {description}: {module_name} - {str(e)}")
        return False

def main():
    """Run dependency validation tests."""
    print("🔍 Validating dependencies for Railway deployment...\n")
    
    # Core dependencies
    tests = [
        ("fastapi", "FastAPI framework"),
        ("uvicorn", "ASGI server"), 
        ("sqlalchemy", "Database ORM"),
        ("pydantic", "Data validation"),
        ("httpx", "HTTP client"),
        ("supabase", "Database client"),
        ("fastmcp", "MCP support"),
        ("crossref_commons", "CrossRef API"),
        ("pymed", "PubMed API"),
        ("trafilatura", "Web content extraction"),
        ("requests", "HTTP requests"),
        ("beautifulsoup4", "HTML parsing"),
        ("lxml", "XML/HTML parser"),
    ]
    
    passed = 0
    total = len(tests)
    
    for module, description in tests:
        if test_import(module, description):
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} dependencies validated")
    
    if passed == total:
        print("🎉 All dependencies are compatible! Railway deployment should succeed.")
        return 0
    else:
        print("⚠️  Some dependencies failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())