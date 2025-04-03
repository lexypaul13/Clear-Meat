#!/usr/bin/env python
"""Script to test rate limiting functionality."""

import requests
import time
import concurrent.futures
import argparse
import sys

def make_request(url, session, req_id):
    """Make a request to the API and return the response."""
    try:
        response = session.get(url)
        headers = response.headers
        
        # Extract rate limit headers if they exist
        rate_limit = headers.get("X-RateLimit-Limit", "N/A")
        remaining = headers.get("X-RateLimit-Remaining", "N/A")
        reset = headers.get("X-RateLimit-Reset", "N/A")
        
        return {
            "id": req_id,
            "status_code": response.status_code,
            "headers": {
                "X-RateLimit-Limit": rate_limit,
                "X-RateLimit-Remaining": remaining,
                "X-RateLimit-Reset": reset
            },
            "content": response.text[:100] + "..." if len(response.text) > 100 else response.text
        }
    except Exception as e:
        return {
            "id": req_id,
            "status_code": "ERROR",
            "error": str(e)
        }

def main():
    """Run the rate limit test."""
    parser = argparse.ArgumentParser(description="Test rate limiting functionality")
    parser.add_argument("--url", default="http://localhost:8000/api/v1/products", help="URL to test")
    parser.add_argument("--requests", type=int, default=50, help="Number of requests to make")
    parser.add_argument("--concurrent", type=int, default=10, help="Number of concurrent requests")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between request batches (seconds)")
    
    args = parser.parse_args()
    
    print(f"Testing rate limiting on {args.url}")
    print(f"Making {args.requests} requests with concurrency of {args.concurrent}")
    
    session = requests.Session()
    responses = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrent) as executor:
        # Submit all requests
        futures = []
        for i in range(args.requests):
            futures.append(executor.submit(make_request, args.url, session, i + 1))
            
            # Add delay between batches
            if (i + 1) % args.concurrent == 0 and i < args.requests - 1:
                time.sleep(args.delay)
        
        # Get results as they complete
        for future in concurrent.futures.as_completed(futures):
            responses.append(future.result())
            
    # Sort responses by ID
    responses.sort(key=lambda x: x["id"])
    
    # Print results
    success_count = sum(1 for r in responses if r["status_code"] == 200)
    rate_limited_count = sum(1 for r in responses if r["status_code"] == 429)
    error_count = sum(1 for r in responses if r["status_code"] not in (200, 429))
    
    print("\nResults:")
    print(f"  Success: {success_count}")
    print(f"  Rate Limited: {rate_limited_count}")
    print(f"  Errors: {error_count}")
    
    if rate_limited_count > 0:
        print("\nRate limiting is working as expected!")
        # Print the first rate limited response
        rate_limited = next((r for r in responses if r["status_code"] == 429), None)
        if rate_limited:
            print("\nFirst rate limited response:")
            print(f"  Request ID: {rate_limited['id']}")
            print(f"  Status Code: {rate_limited['status_code']}")
            print(f"  Response: {rate_limited.get('content', '')}")
            
            # Print the headers from the last successful response before rate limiting
            last_success = next((r for r in responses[:rate_limited['id']-1] if r["status_code"] == 200), None)
            if last_success:
                print("\nLast successful response before rate limiting:")
                print(f"  Request ID: {last_success['id']}")
                print(f"  Rate Limit: {last_success['headers']['X-RateLimit-Limit']}")
                print(f"  Remaining: {last_success['headers']['X-RateLimit-Remaining']}")
    else:
        print("\nNo rate limiting observed. Consider:")
        print("  1. Increasing the number of requests")
        print("  2. Decreasing the delay between requests")
        print("  3. Checking rate limit configuration")

if __name__ == "__main__":
    main() 