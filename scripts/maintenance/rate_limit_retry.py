#!/usr/bin/env python
"""Script to test rate limiting with retry behavior."""

import requests
import time
import argparse
import sys
from datetime import datetime

def make_request(url, session):
    """Make a request and return the response details."""
    try:
        start_time = time.time()
        response = session.get(url)
        end_time = time.time()
        
        return {
            "status_code": response.status_code,
            "time": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "elapsed": round(end_time - start_time, 3),
            "limit": response.headers.get("X-RateLimit-Limit", "N/A"),
            "remaining": response.headers.get("X-RateLimit-Remaining", "N/A"),
            "reset": response.headers.get("X-RateLimit-Reset", "N/A"),
            "retry_after": response.headers.get("Retry-After", "N/A") if response.status_code == 429 else "N/A"
        }
    except Exception as e:
        return {
            "status_code": "ERROR",
            "time": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "error": str(e)
        }

def test_rate_limit_with_retry(url, total_requests, retry_on_429=True, max_retries=3):
    """Test rate limiting with retry behavior."""
    session = requests.Session()
    responses = []
    retry_count = 0
    
    print(f"Testing rate limiting with retry on {url}")
    print(f"Making {total_requests} requests, retry_on_429={retry_on_429}")
    print("\nResults:")
    print(f"{'#':<4} {'Time':<12} {'Status':<6} {'Elapsed(s)':<10} {'Limit':<6} {'Remaining':<9} {'Retry-After':<11}")
    print("-" * 80)
    
    for i in range(total_requests):
        response = make_request(url, session)
        responses.append(response)
        
        # Print current response
        print(f"{i+1:<4} {response['time']:<12} {response['status_code']:<6} "
              f"{response['elapsed'] if 'elapsed' in response else 'N/A':<10} "
              f"{response['limit']:<6} {response['remaining']:<9} "
              f"{response['retry_after']:<11}")
        
        # Handle rate limiting with retry if enabled
        if retry_on_429 and response['status_code'] == 429 and retry_count < max_retries:
            retry_after = response.get('retry_after')
            if retry_after and retry_after != 'N/A':
                retry_seconds = int(retry_after) + 1  # Add 1 second buffer
                retry_count += 1
                
                print(f"\nRate limited! Waiting {retry_seconds} seconds before retry {retry_count}/{max_retries}...")
                time.sleep(retry_seconds)
                
                # Make retry request
                retry_response = make_request(url, session)
                responses.append(retry_response)
                
                print(f"R{retry_count:<3} {retry_response['time']:<12} {retry_response['status_code']:<6} "
                      f"{retry_response['elapsed'] if 'elapsed' in retry_response else 'N/A':<10} "
                      f"{retry_response['limit']:<6} {retry_response['remaining']:<9} "
                      f"{retry_response['retry_after']:<11}")
    
    # Summary
    success_count = sum(1 for r in responses if r['status_code'] == 200)
    rate_limited_count = sum(1 for r in responses if r['status_code'] == 429)
    error_count = sum(1 for r in responses if r['status_code'] not in (200, 429))
    
    print("\nSummary:")
    print(f"  Total Requests: {len(responses)}")
    print(f"  Success: {success_count}")
    print(f"  Rate Limited: {rate_limited_count}")
    print(f"  Errors: {error_count}")
    print(f"  Retries: {retry_count}")
    
    if rate_limited_count > 0:
        print("\nRate limiting is working as expected!")
    else:
        print("\nNo rate limiting observed.")

def main():
    """Run the rate limit test with retry."""
    parser = argparse.ArgumentParser(description="Test rate limiting with retry behavior")
    parser.add_argument("--url", default="http://localhost:8000/api/v1/products", help="URL to test")
    parser.add_argument("--requests", type=int, default=20, help="Number of requests to make")
    parser.add_argument("--no-retry", action="store_true", help="Disable retry on rate limit")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum number of retries")
    
    args = parser.parse_args()
    
    test_rate_limit_with_retry(
        args.url, 
        args.requests, 
        retry_on_429=not args.no_retry,
        max_retries=args.max_retries
    )

if __name__ == "__main__":
    main() 