#!/usr/bin/env python3

"""
External API Test Tool for MeatWise API
--------------------------------------
This script allows testing network calls to any API endpoint.
It provides a simple way to test connectivity and API responses
without requiring a running instance of the MeatWise API.

Example usage:
- Test against local MeatWise API: python test_external_api.py
- Test against a public API: python test_external_api.py https://jsonplaceholder.typicode.com/posts/1
"""

import sys
import requests
import json
from typing import Dict, Any, Optional, List, Tuple

# Default settings
DEFAULT_BASE_URL = "http://localhost:8000/api/v1"
DEFAULT_ENDPOINTS = [
    # Format: (path, method, description)
    ("/health", "GET", "API Health Check"),
    ("/products", "GET", "Product List"),
    ("/products/123456789", "GET", "Specific Product"),
    ("/ingredients", "GET", "Ingredients List")
]

# Example public API for testing when MeatWise API is not available
PUBLIC_API_URL = "https://jsonplaceholder.typicode.com"
PUBLIC_API_ENDPOINTS = [
    # Format: (path, method, description)
    ("/posts/1", "GET", "Get Post #1"),
    ("/users", "GET", "List Users"),
    ("/posts", "GET", "List Posts")
]


def make_request(url: str, method: str = "GET", headers: Optional[Dict] = None,
                 data: Optional[Dict] = None, timeout: int = 10) -> Dict[str, Any]:
    """
    Make a request to the specified URL.
    
    Args:
        url: Full URL to request
        method: HTTP method ("GET", "POST", etc.)
        headers: Request headers
        data: Request data (for POST/PUT)
        timeout: Request timeout in seconds
        
    Returns:
        Dict with response data or error information
    """
    if headers is None:
        headers = {"Content-Type": "application/json"}
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method.upper() == "POST":
            json_data = json.dumps(data) if data else None
            response = requests.post(url, headers=headers, data=json_data, timeout=timeout)
        else:
            return {
                "success": False,
                "status_code": None,
                "error": f"Unsupported method: {method}"
            }
        
        # Try to parse response as JSON
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            response_data = {"text": response.text}
        
        return {
            "success": 200 <= response.status_code < 300,
            "status_code": response.status_code,
            "data": response_data
        }
    
    except requests.ConnectionError:
        return {
            "success": False,
            "status_code": None,
            "error": "Connection error. Is the server running?"
        }
    except requests.Timeout:
        return {
            "success": False,
            "status_code": None,
            "error": f"Request timed out after {timeout} seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": None,
            "error": f"Error: {str(e)}"
        }


def print_header(text: str, char: str = "=") -> None:
    """Print a header with the given text."""
    print(f"\n{char * 80}")
    print(text)
    print(f"{char * 80}")


def print_subheader(text: str) -> None:
    """Print a subheader with the given text."""
    print(f"\n{'-' * 80}")
    print(text)
    print(f"{'-' * 80}")


def print_result(result: Dict[str, Any], verbose: bool = False) -> None:
    """Print the result of a request."""
    if result["success"]:
        status = f"SUCCESS (Status: {result['status_code']})"
        print(f"✅ {status}")
        
        # Print response data
        if verbose:
            print("\nResponse data:")
            if isinstance(result["data"], dict) or isinstance(result["data"], list):
                print(json.dumps(result["data"], indent=2))
            else:
                print(result["data"])
        else:
            # Print a summary of the response
            if isinstance(result["data"], dict):
                # For dictionary responses, show the keys
                print(f"Response keys: {', '.join(result['data'].keys())}")
                # If it's a list of items, show the count
                for key, value in result["data"].items():
                    if isinstance(value, list) and value:
                        print(f"  - {key}: {len(value)} items")
            elif isinstance(result["data"], list):
                # For list responses, show the count
                print(f"Response contains {len(result['data'])} items")
                if result["data"] and isinstance(result["data"][0], dict):
                    # Show keys from the first item
                    print(f"First item keys: {', '.join(result['data'][0].keys())}")
    else:
        status = f"FAILED"
        if result.get("status_code"):
            status += f" (Status: {result['status_code']})"
        print(f"❌ {status}")
        print(f"Error: {result.get('error', 'Unknown error')}")


def test_endpoints(base_url: str, endpoints: List[Tuple[str, str, str]], 
                   verbose: bool = False) -> Tuple[int, int]:
    """
    Test the given endpoints against the base URL.
    
    Args:
        base_url: Base URL for the API
        endpoints: List of (path, method, description) tuples
        verbose: Whether to print verbose output
        
    Returns:
        Tuple of (success_count, total_count)
    """
    success_count = 0
    total_count = len(endpoints)
    
    for path, method, description in endpoints:
        # Construct the full URL
        url = f"{base_url}{path}"
        
        # Print the test description
        print_subheader(f"Testing: {description}")
        print(f"URL: {url}")
        print(f"Method: {method}")
        
        # Make the request
        result = make_request(url, method)
        
        # Print the result
        print_result(result, verbose)
        
        # Update success count
        if result["success"]:
            success_count += 1
    
    return success_count, total_count


def main():
    """Main function."""
    # Parse command-line arguments
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
        # Check if it's a public API test
        if base_url == "--public":
            base_url = PUBLIC_API_URL
            endpoints = PUBLIC_API_ENDPOINTS
        else:
            # Use default endpoints for custom URL
            endpoints = DEFAULT_ENDPOINTS
    else:
        # Use defaults
        base_url = DEFAULT_BASE_URL
        endpoints = DEFAULT_ENDPOINTS
    
    # Check for verbose flag
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    
    # Print info
    print_header(f"API Test Tool")
    print(f"Base URL: {base_url}")
    print(f"Verbose: {'Yes' if verbose else 'No'}")
    print(f"Testing {len(endpoints)} endpoints...")
    
    # Run the tests
    success_count, total_count = test_endpoints(base_url, endpoints, verbose)
    
    # Print summary
    print_header(f"Test Summary")
    print(f"Tests passed: {success_count}/{total_count}")
    print(f"Tests failed: {total_count - success_count}/{total_count}")
    
    # Exit with appropriate code
    sys.exit(0 if success_count == total_count else 1)


if __name__ == "__main__":
    main() 