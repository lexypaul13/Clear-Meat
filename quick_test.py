#!/usr/bin/env python3
"""
Quick deployment test - Tests only the most critical endpoints.
Use this for fast verification during development.
"""

import requests
import sys
import time

def test_api(base_url="http://localhost:8000"):
    """Quick test of critical endpoints."""
    print(f"🚀 Quick testing Clear-Meat API at {base_url}")
    print("=" * 50)
    
    tests = [
        ("Health Check", "GET", "/health"),
        ("Product Count", "GET", "/api/v1/products/count"),
        ("Products List", "GET", "/api/v1/products/?limit=1"),
        ("API Docs", "GET", "/docs"),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, method, endpoint in tests:
        try:
            start_time = time.time()
            response = requests.request(method, f"{base_url}{endpoint}", timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                print(f"✅ {name}: PASS ({response_time:.0f}ms)")
                passed += 1
            else:
                print(f"❌ {name}: FAIL (HTTP {response.status_code})")
                
        except Exception as e:
            print(f"❌ {name}: ERROR ({str(e)})")
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All critical tests PASSED! API is working.")
        return True
    else:
        print("⚠️  Some tests FAILED. Check the issues above.")
        return False

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    success = test_api(url)
    sys.exit(0 if success else 1)