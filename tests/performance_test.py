#!/usr/bin/env python3
"""
Clear-Meat API Performance Testing Suite
Tests concurrent load, response times, and bottlenecks
"""

import asyncio
import aiohttp
import time
import statistics
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class TestResult:
    endpoint: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    requests_per_second: float
    errors: List[str]

class PerformanceTestSuite:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[TestResult] = []
        
    async def single_request(self, session: aiohttp.ClientSession, url: str, method: str = "GET", 
                           data: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """Make a single HTTP request and measure response time"""
        start_time = time.time()
        try:
            if method == "POST":
                async with session.post(url, json=data, headers=headers) as response:
                    response_time = time.time() - start_time
                    return {
                        "success": True,
                        "response_time": response_time,
                        "status_code": response.status,
                        "error": None
                    }
            else:
                async with session.get(url, headers=headers) as response:
                    response_time = time.time() - start_time
                    return {
                        "success": True,
                        "response_time": response_time,
                        "status_code": response.status,
                        "error": None
                    }
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "success": False,
                "response_time": response_time,
                "status_code": 0,
                "error": str(e)
            }

    async def load_test_endpoint(self, endpoint: str, concurrent_users: int, 
                               total_requests: int, method: str = "GET",
                               data: Dict = None, headers: Dict = None) -> TestResult:
        """Run load test on a specific endpoint"""
        print(f"🔥 Testing {endpoint} - {concurrent_users} users, {total_requests} requests")
        
        connector = aiohttp.TCPConnector(limit=200, limit_per_host=100)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Create semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(concurrent_users)
            
            async def bounded_request():
                async with semaphore:
                    return await self.single_request(session, endpoint, method, data, headers)
            
            # Start timer for throughput calculation
            start_time = time.time()
            
            # Execute all requests
            tasks = [bounded_request() for _ in range(total_requests)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_duration = end_time - start_time
        
        # Analyze results
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        if successful_results:
            response_times = [r["response_time"] for r in successful_results]
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = 0
            
        requests_per_second = total_requests / total_duration if total_duration > 0 else 0
        errors = [r["error"] for r in failed_results if r["error"]]
        
        return TestResult(
            endpoint=endpoint,
            total_requests=total_requests,
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            requests_per_second=requests_per_second,
            errors=errors[:5]  # Limit error samples
        )

    async def test_health_endpoint(self):
        """Test health check endpoint"""
        endpoint = f"{self.base_url}/health"
        result = await self.load_test_endpoint(endpoint, 10, 100)
        self.results.append(result)

    async def test_search_endpoint(self):
        """Test natural language search (CPU intensive)"""
        endpoint = f"{self.base_url}/api/v1/products/nlp-search?q=healthy%20chicken&limit=5"
        result = await self.load_test_endpoint(endpoint, 5, 50)  # Lower load for AI endpoint
        self.results.append(result)

    async def test_product_listing(self):
        """Test product listing (DB intensive)"""
        endpoint = f"{self.base_url}/api/v1/products/?limit=20"
        result = await self.load_test_endpoint(endpoint, 20, 200)
        self.results.append(result)

    async def test_authentication(self):
        """Test authentication endpoint"""
        endpoint = f"{self.base_url}/api/v1/auth/login"
        login_data = {
            "username": "working-test@example.com",
            "password": "securepass123"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        # Convert to form data
        form_data = "&".join([f"{k}={v}" for k, v in login_data.items()])
        
        result = await self.load_test_endpoint(endpoint, 10, 100, "POST", form_data, headers)
        self.results.append(result)

    def print_results(self):
        """Print comprehensive test results"""
        print("\n" + "="*80)
        print("🚀 CLEAR-MEAT API PERFORMANCE TEST RESULTS")
        print("="*80)
        
        for result in self.results:
            print(f"\n📊 {result.endpoint}")
            print(f"   Total Requests: {result.total_requests}")
            print(f"   ✅ Successful: {result.successful_requests}")
            print(f"   ❌ Failed: {result.failed_requests}")
            print(f"   📈 Success Rate: {(result.successful_requests/result.total_requests)*100:.1f}%")
            print(f"   ⚡ Requests/sec: {result.requests_per_second:.2f}")
            print(f"   ⏱️  Avg Response: {result.avg_response_time*1000:.1f}ms")
            print(f"   ⏱️  Min Response: {result.min_response_time*1000:.1f}ms")
            print(f"   ⏱️  Max Response: {result.max_response_time*1000:.1f}ms")
            print(f"   ⏱️  95th Percentile: {result.p95_response_time*1000:.1f}ms")
            
            if result.errors:
                print(f"   🚨 Sample Errors: {result.errors[:3]}")
        
        print("\n" + "="*80)
        print("📋 SUMMARY")
        print("="*80)
        
        total_requests = sum(r.total_requests for r in self.results)
        total_successful = sum(r.successful_requests for r in self.results)
        overall_success_rate = (total_successful / total_requests) * 100 if total_requests > 0 else 0
        
        print(f"🎯 Overall Success Rate: {overall_success_rate:.1f}%")
        print(f"📊 Total Requests Tested: {total_requests}")
        print(f"✅ Total Successful: {total_successful}")
        
        # Performance recommendations
        self.print_recommendations()

    def print_recommendations(self):
        """Print performance recommendations based on results"""
        print("\n🔧 PERFORMANCE RECOMMENDATIONS:")
        
        for result in self.results:
            if result.avg_response_time > 1.0:  # > 1 second
                print(f"⚠️  {result.endpoint}: Slow response ({result.avg_response_time*1000:.0f}ms) - Consider optimization")
            
            if result.requests_per_second < 10:
                print(f"⚠️  {result.endpoint}: Low throughput ({result.requests_per_second:.1f} req/s) - Check bottlenecks")
            
            if result.failed_requests > 0:
                print(f"🚨 {result.endpoint}: {result.failed_requests} failures - Check error handling")

async def main():
    """Run all performance tests"""
    print("🔥 Starting Clear-Meat API Performance Tests...")
    
    tester = PerformanceTestSuite()
    
    # Run tests sequentially to avoid overwhelming the server
    await tester.test_health_endpoint()
    await asyncio.sleep(2)  # Brief pause between tests
    
    await tester.test_product_listing()
    await asyncio.sleep(2)
    
    await tester.test_search_endpoint()
    await asyncio.sleep(2)
    
    await tester.test_authentication()
    
    # Print results
    tester.print_results()

if __name__ == "__main__":
    asyncio.run(main()) 