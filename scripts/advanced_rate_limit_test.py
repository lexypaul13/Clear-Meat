#!/usr/bin/env python
"""Advanced script to test rate limiting functionality in different scenarios."""

import requests
import time
import concurrent.futures
import argparse
import sys
import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

def make_request(url, session, req_id, headers=None):
    """Make a request to the API and return the response."""
    try:
        start_time = time.time()
        response = session.get(url, headers=headers)
        end_time = time.time()
        
        response_time = end_time - start_time
        response_headers = response.headers
        
        # Extract rate limit headers if they exist
        rate_limit = response_headers.get("X-RateLimit-Limit", "N/A")
        remaining = response_headers.get("X-RateLimit-Remaining", "N/A")
        reset = response_headers.get("X-RateLimit-Reset", "N/A")
        
        return {
            "id": req_id,
            "timestamp": datetime.now().isoformat(),
            "elapsed": response_time,
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
            "timestamp": datetime.now().isoformat(),
            "status_code": "ERROR",
            "error": str(e)
        }

def analyze_results(responses, output_file=None):
    """Analyze test results and optionally output to a file."""
    success_count = sum(1 for r in responses if r["status_code"] == 200)
    rate_limited_count = sum(1 for r in responses if r["status_code"] == 429)
    error_count = sum(1 for r in responses if r["status_code"] not in (200, 429))
    
    results = {
        "summary": {
            "total_requests": len(responses),
            "success_count": success_count,
            "rate_limited_count": rate_limited_count,
            "error_count": error_count
        },
        "responses": responses
    }
    
    # Write to file if specified
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
            print(f"Results written to {output_file}")
    
    return results

def plot_results(responses, title="Rate Limit Test Results", output_file=None):
    """Plot the test results."""
    # Extract data for plotting
    request_ids = [r["id"] for r in responses]
    status_codes = [r["status_code"] if isinstance(r["status_code"], int) else 0 for r in responses]
    rate_limits = [int(r["headers"].get("X-RateLimit-Limit", 0)) if "headers" in r else 0 for r in responses]
    remaining = [int(r["headers"].get("X-RateLimit-Remaining", 0)) if "headers" in r else 0 for r in responses]
    
    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot status codes
    ax1.plot(request_ids, status_codes, 'o-', color='blue')
    ax1.set_xlabel('Request ID')
    ax1.set_ylabel('Status Code')
    ax1.set_title('Response Status Codes')
    ax1.grid(True)
    
    # Red line at 429 to highlight rate limit
    ax1.axhline(y=429, color='r', linestyle='-', alpha=0.3)
    
    # Plot rate limit headers
    ax2.plot(request_ids, remaining, 'o-', color='green', label='Remaining')
    ax2.set_xlabel('Request ID')
    ax2.set_ylabel('Requests Remaining')
    ax2.set_title('Rate Limit Headers')
    ax2.grid(True)
    ax2.legend()
    
    # Set suptitle
    plt.suptitle(title, fontsize=16)
    plt.tight_layout()
    
    # Save or show the plot
    if output_file:
        plt.savefig(output_file)
        print(f"Plot saved to {output_file}")
    else:
        plt.show()

def burst_test(url, burst_size, session):
    """Perform a burst test with many requests at once."""
    print(f"\nBurst Test: Sending {burst_size} concurrent requests to {url}")
    
    responses = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=burst_size) as executor:
        futures = [executor.submit(make_request, url, session, i + 1) for i in range(burst_size)]
        
        for future in concurrent.futures.as_completed(futures):
            responses.append(future.result())
    
    # Sort responses by ID
    responses.sort(key=lambda x: x["id"])
    
    # Analyze results
    summary = analyze_results(responses)["summary"]
    print("\nBurst Test Results:")
    print(f"  Total Requests: {summary['total_requests']}")
    print(f"  Success: {summary['success_count']}")
    print(f"  Rate Limited: {summary['rate_limited_count']}")
    print(f"  Errors: {summary['error_count']}")
    
    return responses

def sustained_test(url, total_requests, rate, session):
    """Perform a sustained test with a specific request rate."""
    delay = 1 / rate if rate > 0 else 0
    print(f"\nSustained Test: Sending {total_requests} requests at ~{rate}/second to {url}")
    
    responses = []
    
    start_time = time.time()
    for i in range(total_requests):
        response = make_request(url, session, i + 1)
        responses.append(response)
        
        # Add delay to maintain rate (accounting for request time)
        if i < total_requests - 1:  # Don't delay after the last request
            elapsed = time.time() - start_time
            target_time = (i + 1) / rate
            sleep_time = max(0, target_time - elapsed)
            time.sleep(sleep_time)
    
    # Analyze results
    actual_rate = total_requests / (time.time() - start_time)
    summary = analyze_results(responses)["summary"]
    print("\nSustained Test Results:")
    print(f"  Total Requests: {summary['total_requests']}")
    print(f"  Success: {summary['success_count']}")
    print(f"  Rate Limited: {summary['rate_limited_count']}")
    print(f"  Errors: {summary['error_count']}")
    print(f"  Actual Rate: {actual_rate:.2f} requests/second")
    
    return responses

def main():
    """Run the advanced rate limit testing."""
    parser = argparse.ArgumentParser(description="Advanced rate limit testing")
    parser.add_argument("--url", default="http://localhost:8000/api/v1/products", help="URL to test")
    parser.add_argument("--mode", choices=["burst", "sustained", "both"], default="both", 
                        help="Test mode: burst, sustained, or both")
    parser.add_argument("--burst-size", type=int, default=50, help="Number of requests in burst test")
    parser.add_argument("--sustained-requests", type=int, default=60, 
                        help="Number of requests in sustained test")
    parser.add_argument("--sustained-rate", type=float, default=2.0, 
                        help="Requests per second in sustained test")
    parser.add_argument("--output", help="Output file for JSON results")
    parser.add_argument("--plot", help="Output file for results plot")
    
    args = parser.parse_args()
    
    # Main session for all requests
    session = requests.Session()
    
    all_responses = []
    summary = None
    
    # Run selected test modes
    if args.mode in ["burst", "both"]:
        burst_responses = burst_test(args.url, args.burst_size, session)
        all_responses.extend(burst_responses)
        
        if args.plot and args.mode == "burst":
            plot_results(burst_responses, "Burst Test Results", args.plot)
    
    if args.mode in ["sustained", "both"]:
        sustained_responses = sustained_test(args.url, args.sustained_requests, args.sustained_rate, session)
        all_responses.extend(sustained_responses)
        
        if args.plot and args.mode == "sustained":
            plot_results(sustained_responses, "Sustained Test Results", args.plot)
    
    # Overall results
    if args.mode == "both":
        print("\nOverall Results:")
        summary = analyze_results(all_responses, args.output)["summary"]
        print(f"  Total Requests: {summary['total_requests']}")
        print(f"  Success: {summary['success_count']}")
        print(f"  Rate Limited: {summary['rate_limited_count']}")
        print(f"  Errors: {summary['error_count']}")
        
        if args.plot:
            plot_results(all_responses, "Rate Limit Test Results (All Tests)", args.plot)
    else:
        # For single mode, use the existing responses
        summary = analyze_results(all_responses, args.output)["summary"]
    
    if summary and summary['rate_limited_count'] > 0:
        print("\nRate limiting is working as expected!")
    else:
        print("\nNo rate limiting observed. Consider:")
        print("  1. Increasing the number or rate of requests")
        print("  2. Checking rate limit configuration")

if __name__ == "__main__":
    try:
        import matplotlib
        main()
    except ImportError:
        print("Error: matplotlib required for plotting.")
        print("Install with: pip install matplotlib")
        print("You can still run the tests without plotting by not specifying --plot")
        sys.exit(1) 