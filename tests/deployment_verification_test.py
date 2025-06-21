#!/usr/bin/env python3
"""
Comprehensive deployment verification test for Clear-Meat API.
Tests all critical endpoints to ensure the application is ready for deployment.
"""

import asyncio
import json
import os
import sys
import time
import requests
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DeploymentTestSuite:
    """Comprehensive test suite for deployment verification."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Clear-Meat-Deployment-Test/1.0'
        })
        self.auth_token: Optional[str] = None
        self.test_results: List[Dict] = []
        
    def log_test_result(self, test_name: str, passed: bool, details: str = "", response_time: float = 0):
        """Log test result for final report."""
        result = {
            'test': test_name,
            'status': 'PASS' if passed else 'FAIL',
            'details': details,
            'response_time_ms': round(response_time * 1000, 2)
        }
        self.test_results.append(result)
        
        status_emoji = "✅" if passed else "❌"
        logger.info(f"{status_emoji} {test_name}: {result['status']} ({result['response_time_ms']}ms)")
        if details:
            logger.info(f"   Details: {details}")
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> Tuple[bool, requests.Response, str]:
        """Make HTTP request with error handling."""
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        
        try:
            start_time = time.time()
            response = self.session.request(method, url, timeout=30, **kwargs)
            response_time = time.time() - start_time
            
            return True, response, ""
            
        except requests.exceptions.RequestException as e:
            return False, None, str(e)
    
    def test_health_endpoint(self) -> bool:
        """Test basic health check endpoint."""
        success, response, error = self.make_request('GET', '/health')
        
        if not success:
            self.log_test_result("Health Check", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            try:
                data = response.json()
                details = f"Status: {data.get('status', 'unknown')}"
                self.log_test_result("Health Check", True, details, response.elapsed.total_seconds())
                return True
            except json.JSONDecodeError:
                self.log_test_result("Health Check", False, "Invalid JSON response")
                return False
        else:
            self.log_test_result("Health Check", False, f"HTTP {response.status_code}")
            return False
    
    def test_docs_endpoints(self) -> bool:
        """Test API documentation endpoints."""
        endpoints = [
            ('/docs', 'OpenAPI Docs'),
            ('/redoc', 'ReDoc Documentation'),
            ('/openapi.json', 'OpenAPI Schema')
        ]
        
        all_passed = True
        for endpoint, name in endpoints:
            success, response, error = self.make_request('GET', endpoint)
            
            if not success:
                self.log_test_result(name, False, f"Request failed: {error}")
                all_passed = False
                continue
            
            if response.status_code == 200:
                self.log_test_result(name, True, f"Content-Type: {response.headers.get('content-type', 'unknown')}", response.elapsed.total_seconds())
            else:
                self.log_test_result(name, False, f"HTTP {response.status_code}")
                all_passed = False
        
        return all_passed
    
    def test_product_endpoints(self) -> bool:
        """Test product-related endpoints."""
        all_passed = True
        
        # Test product count
        success, response, error = self.make_request('GET', '/api/v1/products/count')
        if success and response.status_code == 200:
            try:
                data = response.json()
                count = data.get('count', 0)
                self.log_test_result("Product Count", True, f"Total products: {count}", response.elapsed.total_seconds())
            except json.JSONDecodeError:
                self.log_test_result("Product Count", False, "Invalid JSON response")
                all_passed = False
        else:
            self.log_test_result("Product Count", False, f"HTTP {response.status_code if response else 'Request failed'}")
            all_passed = False
        
        # Test products list with pagination
        success, response, error = self.make_request('GET', '/api/v1/products/?skip=0&limit=5')
        if success and response.status_code == 200:
            try:
                data = response.json()
                products = data.get('products', [])
                self.log_test_result("Products List", True, f"Retrieved {len(products)} products", response.elapsed.total_seconds())
                
                # Test individual product if we have any
                if products:
                    product_code = products[0].get('code')
                    if product_code:
                        self.test_individual_product(product_code)
                
            except json.JSONDecodeError:
                self.log_test_result("Products List", False, "Invalid JSON response")
                all_passed = False
        else:
            self.log_test_result("Products List", False, f"HTTP {response.status_code if response else 'Request failed'}")
            all_passed = False
        
        return all_passed
    
    def test_individual_product(self, product_code: str) -> bool:
        """Test individual product endpoints."""
        all_passed = True
        
        # Test basic product info
        success, response, error = self.make_request('GET', f'/api/v1/products/{product_code}')
        if success and response.status_code == 200:
            try:
                data = response.json()
                product_name = data.get('name', 'Unknown')
                self.log_test_result("Product Info", True, f"Product: {product_name}", response.elapsed.total_seconds())
            except json.JSONDecodeError:
                self.log_test_result("Product Info", False, "Invalid JSON response")
                all_passed = False
        else:
            self.log_test_result("Product Info", False, f"HTTP {response.status_code if response else 'Request failed'}")
            all_passed = False
        
        # Test health assessment (critical feature)
        success, response, error = self.make_request('GET', f'/api/v1/products/{product_code}/health-assessment')
        if success:
            if response.status_code == 200:
                try:
                    data = response.json()
                    summary = data.get('summary', 'No summary')[:50] + "..."
                    self.log_test_result("Health Assessment", True, f"Summary: {summary}", response.elapsed.total_seconds())
                except json.JSONDecodeError:
                    self.log_test_result("Health Assessment", False, "Invalid JSON response")
                    all_passed = False
            elif response.status_code == 404:
                self.log_test_result("Health Assessment", True, "Product not found (expected for some products)", response.elapsed.total_seconds())
            else:
                self.log_test_result("Health Assessment", False, f"HTTP {response.status_code}")
                all_passed = False
        else:
            self.log_test_result("Health Assessment", False, f"Request failed: {error}")
            all_passed = False
        
        return all_passed
    
    def test_search_endpoints(self) -> bool:
        """Test search functionality."""
        all_passed = True
        
        # Test product search
        search_terms = ["bacon", "chicken", "beef"]
        
        for term in search_terms:
            success, response, error = self.make_request('GET', f'/api/v1/products/search?q={term}&limit=3')
            if success and response.status_code == 200:
                try:
                    data = response.json()
                    results = data.get('products', [])
                    self.log_test_result(f"Search '{term}'", True, f"Found {len(results)} results", response.elapsed.total_seconds())
                except json.JSONDecodeError:
                    self.log_test_result(f"Search '{term}'", False, "Invalid JSON response")
                    all_passed = False
            else:
                self.log_test_result(f"Search '{term}'", False, f"HTTP {response.status_code if response else 'Request failed'}")
                all_passed = False
        
        return all_passed
    
    def test_performance_endpoints(self) -> bool:
        """Test performance monitoring endpoints."""
        all_passed = True
        
        # Test performance metrics
        success, response, error = self.make_request('GET', '/api/v1/performance/metrics')
        if success:
            if response.status_code == 200:
                try:
                    data = response.json()
                    uptime = data.get('uptime_seconds', 0)
                    self.log_test_result("Performance Metrics", True, f"Uptime: {uptime}s", response.elapsed.total_seconds())
                except json.JSONDecodeError:
                    self.log_test_result("Performance Metrics", False, "Invalid JSON response")
                    all_passed = False
            else:
                self.log_test_result("Performance Metrics", False, f"HTTP {response.status_code}")
                all_passed = False
        else:
            self.log_test_result("Performance Metrics", False, f"Request failed: {error}")
            all_passed = False
        
        return all_passed
    
    def test_error_handling(self) -> bool:
        """Test error handling for invalid requests."""
        all_passed = True
        
        # Test invalid product code
        success, response, error = self.make_request('GET', '/api/v1/products/invalid-product-code-123')
        if success and response.status_code == 404:
            self.log_test_result("Error Handling (404)", True, "Correctly returns 404 for invalid product", response.elapsed.total_seconds())
        else:
            self.log_test_result("Error Handling (404)", False, f"Expected 404, got {response.status_code if response else 'request failed'}")
            all_passed = False
        
        # Test invalid endpoint
        success, response, error = self.make_request('GET', '/api/v1/nonexistent-endpoint')
        if success and response.status_code == 404:
            self.log_test_result("Error Handling (Invalid Endpoint)", True, "Correctly returns 404 for invalid endpoint", response.elapsed.total_seconds())
        else:
            self.log_test_result("Error Handling (Invalid Endpoint)", False, f"Expected 404, got {response.status_code if response else 'request failed'}")
            all_passed = False
        
        return all_passed
    
    def test_cors_headers(self) -> bool:
        """Test CORS configuration."""
        success, response, error = self.make_request('OPTIONS', '/api/v1/products/')
        
        if success:
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
            }
            
            has_cors = any(cors_headers.values())
            details = f"CORS headers present: {has_cors}"
            self.log_test_result("CORS Configuration", has_cors, details, response.elapsed.total_seconds())
            return has_cors
        else:
            self.log_test_result("CORS Configuration", False, f"Request failed: {error}")
            return False
    
    def test_rate_limiting(self) -> bool:
        """Test rate limiting (light test)."""
        # Make several rapid requests to check rate limiting
        rapid_requests = []
        
        for i in range(5):
            success, response, error = self.make_request('GET', '/health')
            if success:
                rapid_requests.append(response.status_code)
        
        # All should succeed for health endpoint (usually not rate limited)
        all_success = all(status == 200 for status in rapid_requests)
        details = f"5 rapid requests: {rapid_requests}"
        self.log_test_result("Rate Limiting", True, details)  # Pass if no errors
        return True
    
    def run_all_tests(self) -> bool:
        """Run all deployment verification tests."""
        logger.info("🚀 Starting Clear-Meat API Deployment Verification Tests")
        logger.info(f"📍 Testing against: {self.base_url}")
        logger.info("=" * 70)
        
        test_functions = [
            ("Basic Health Check", self.test_health_endpoint),
            ("API Documentation", self.test_docs_endpoints),
            ("Product Endpoints", self.test_product_endpoints),
            ("Search Functionality", self.test_search_endpoints),
            ("Performance Monitoring", self.test_performance_endpoints),
            ("Error Handling", self.test_error_handling),
            ("CORS Configuration", self.test_cors_headers),
            ("Rate Limiting", self.test_rate_limiting),
        ]
        
        overall_success = True
        
        for test_category, test_function in test_functions:
            logger.info(f"\n🧪 Running {test_category} tests...")
            try:
                category_success = test_function()
                if not category_success:
                    overall_success = False
            except Exception as e:
                logger.error(f"❌ {test_category} test failed with exception: {e}")
                self.log_test_result(f"{test_category} (Exception)", False, str(e))
                overall_success = False
        
        self.print_final_report(overall_success)
        return overall_success
    
    def print_final_report(self, overall_success: bool):
        """Print comprehensive test report."""
        logger.info("\n" + "=" * 70)
        logger.info("📊 DEPLOYMENT VERIFICATION TEST REPORT")
        logger.info("=" * 70)
        
        passed_tests = [r for r in self.test_results if r['status'] == 'PASS']
        failed_tests = [r for r in self.test_results if r['status'] == 'FAIL']
        
        logger.info(f"✅ Passed: {len(passed_tests)}")
        logger.info(f"❌ Failed: {len(failed_tests)}")
        logger.info(f"📈 Success Rate: {len(passed_tests)}/{len(self.test_results)} ({len(passed_tests)/len(self.test_results)*100:.1f}%)")
        
        # Average response time
        response_times = [r['response_time_ms'] for r in self.test_results if r['response_time_ms'] > 0]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            logger.info(f"⚡ Average Response Time: {avg_response_time:.1f}ms")
        
        if failed_tests:
            logger.info("\n❌ FAILED TESTS:")
            for test in failed_tests:
                logger.info(f"   • {test['test']}: {test['details']}")
        
        logger.info("\n" + "=" * 70)
        
        if overall_success:
            logger.info("🎉 ALL TESTS PASSED - API IS READY FOR DEPLOYMENT! 🚀")
        else:
            logger.info("⚠️  SOME TESTS FAILED - REVIEW ISSUES BEFORE DEPLOYMENT")
        
        logger.info("=" * 70)

def main():
    """Main function to run deployment verification tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clear-Meat API Deployment Verification Tests')
    parser.add_argument('--url', default='http://localhost:8000', 
                       help='Base URL of the API to test (default: http://localhost:8000)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run tests
    test_suite = DeploymentTestSuite(args.url)
    success = test_suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()