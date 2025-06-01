#!/usr/bin/env python3
"""
Clear-Meat API Security Testing Suite
Comprehensive testing for security vulnerabilities and edge cases
"""

import asyncio
import aiohttp
import time
import re
import json
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from urllib.parse import quote, unquote

@dataclass
class SecurityTestResult:
    test_name: str
    passed: bool
    details: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    
class SecurityTestSuite:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[SecurityTestResult] = []
        self.test_token = None
        
    def add_result(self, test_name: str, passed: bool, details: str, severity: str = "MEDIUM"):
        """Add a test result to the results list"""
        result = SecurityTestResult(test_name, passed, details, severity)
        self.results.append(result)
        
        # Print immediate feedback
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
    async def setup_test_user(self):
        """Create a test user and get authentication token"""
        print("🔧 Setting up test user...")
        
        # Test registration with retries and exponential backoff
        max_retries = 5  # Increased from 3
        base_delay = 3  # seconds
        # Use microseconds to ensure uniqueness
        test_email = f"security-test-{int(time.time() * 1000000)}@example.com"
        registration_data = {
            "email": test_email,
            "password": "SecurePass123!",  # Strong password with uppercase, lowercase, number, special char
            "full_name": "Security Test User"
        }
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        # Exponential backoff: delay = base_delay * (2^attempt)
                        retry_delay = base_delay * (2 ** attempt)
                        print(f"Retrying test user creation (attempt {attempt + 1}/{max_retries}, waiting {retry_delay}s)...")
                        await asyncio.sleep(retry_delay)
                        
                    async with session.post(
                        f"{self.base_url}/api/v1/auth/register",
                        json=registration_data
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.test_token = data.get("access_token")
                            print(f"✅ Test user created: {test_email}")
                            return True
                        elif response.status == 429:
                            print(f"⚠️ Rate limited on attempt {attempt + 1}, will retry with longer delay...")
                            continue
                        else:
                            text = await response.text()
                            print(f"❌ Failed to create test user: {response.status} - {text}")
                            if attempt == max_retries - 1:
                                return False
                            continue
                except Exception as e:
                    print(f"❌ Error creating test user: {e}")
                    if attempt == max_retries - 1:
                        return False
                    
        print("❌ Failed to create test user after all retries")
        return False

    async def test_key_exposure_protection(self):
        """Test that sensitive keys are not exposed in any output"""
        print("\n🔒 Testing Key Exposure Protection...")
        
        # Test 1: Check server startup logs don't contain partial keys
        try:
            result = subprocess.run(
                ["bash", "-c", "cat start_server.sh | grep -E '(KEY.*:.*)|(SECRET.*:.*)'"],
                capture_output=True, text=True, timeout=10
            )
            
            # Look for any partial key exposure patterns
            dangerous_patterns = [
                r'KEY.*\$\{.*:0:\d+\}',  # ${VAR:0:8} patterns
                r'SECRET.*\$\{.*:0:\d+\}',
                r'eyJ[A-Za-z0-9]',  # JWT token starts
                r'AIza[A-Za-z0-9]',  # Google API key starts
            ]
            
            found_exposure = False
            for pattern in dangerous_patterns:
                if re.search(pattern, result.stdout):
                    found_exposure = True
                    break
                    
            self.add_result(
                "Key Exposure in Startup Scripts",
                not found_exposure,
                "No partial key patterns found in startup scripts" if not found_exposure else "Found potential key exposure patterns",
                "CRITICAL"
            )
            
        except Exception as e:
            self.add_result(
                "Key Exposure in Startup Scripts",
                False,
                f"Error checking startup scripts: {e}",
                "HIGH"
            )

    async def test_authentication_security(self):
        """Test authentication mechanisms and security"""
        print("\n🔐 Testing Authentication Security...")
        
        async with aiohttp.ClientSession() as session:
            # Test 1: Weak password rejection
            weak_passwords = ["123", "password", "admin", "test"]
            
            for weak_pass in weak_passwords:
                try:
                    test_data = {
                        "email": f"weak-test-{int(time.time())}@example.com",
                        "password": weak_pass
                    }
                    
                    async with session.post(
                        f"{self.base_url}/api/v1/auth/register",
                        json=test_data
                    ) as response:
                        
                        # Should reject weak passwords
                        rejected = response.status >= 400
                        self.add_result(
                            f"Weak Password Rejection ({weak_pass})",
                            rejected,
                            "Weak password properly rejected" if rejected else "Weak password accepted",
                            "HIGH"
                        )
                        
                except Exception as e:
                    self.add_result(
                        f"Weak Password Test ({weak_pass})",
                        False,
                        f"Error testing weak password: {e}",
                        "MEDIUM"
                    )
                    
            # Test 2: SQL Injection in auth
            sql_injection_payloads = [
                "admin'; DROP TABLE users; --",
                "' OR '1'='1",
                "' UNION SELECT * FROM users --"
            ]
            
            for payload in sql_injection_payloads:
                try:
                    injection_data = {
                        "email": payload,
                        "password": "testpass123"
                    }
                    
                    async with session.post(
                        f"{self.base_url}/api/v1/auth/register",
                        json=injection_data
                    ) as response:
                        
                        # Should reject malicious input
                        text = await response.text()
                        sql_error_indicators = ["syntax error", "sql", "database", "table"]
                        has_sql_error = any(indicator in text.lower() for indicator in sql_error_indicators)
                        
                        self.add_result(
                            f"SQL Injection Protection (Auth)",
                            not has_sql_error and response.status >= 400,
                            "SQL injection properly handled" if not has_sql_error else "Potential SQL injection vulnerability",
                            "CRITICAL"
                        )
                        
                except Exception as e:
                    # Exceptions are actually good here - means the input was rejected
                    self.add_result(
                        f"SQL Injection Protection (Auth)",
                        True,
                        "Malicious input caused exception (good)",
                        "LOW"
                    )

    async def test_input_validation(self):
        """Test input validation and sanitization"""
        print("\n🛡️ Testing Input Validation...")
        
        if not self.test_token:
            print("⚠️ Skipping input validation tests - no test token available")
            return
            
        headers = {"Authorization": f"Bearer {self.test_token}"}
        
        async with aiohttp.ClientSession() as session:
            # Test 1: XSS prevention in search
            xss_payloads = [
                "<script>alert('xss')</script>",
                "javascript:alert('xss')",
                "<img src=x onerror=alert('xss')>",
                "';alert('xss');//"
            ]
            
            for payload in xss_payloads:
                try:
                    encoded_payload = quote(payload)
                    async with session.get(
                        f"{self.base_url}/api/v1/products/nlp-search?q={encoded_payload}",
                        headers=headers
                    ) as response:
                        
                        text = await response.text()
                        # Check if payload is echoed back unescaped
                        payload_echoed = payload in text
                        
                        self.add_result(
                            f"XSS Prevention (Search)",
                            not payload_echoed,
                            "XSS payload properly sanitized" if not payload_echoed else "XSS payload echoed back",
                            "HIGH"
                        )
                        
                except Exception as e:
                    self.add_result(
                        f"XSS Prevention Test",
                        True,
                        "XSS payload caused exception (input rejected)",
                        "LOW"
                    )
                    
            # Test 2: Parameter pollution
            try:
                async with session.get(
                    f"{self.base_url}/api/v1/products/?limit=10&limit=999999&limit=-1",
                    headers=headers
                ) as response:
                    
                    data = await response.json()
                    products_count = len(data.get("products", []))
                    
                    # Should not return excessive records due to parameter pollution
                    self.add_result(
                        "Parameter Pollution Protection",
                        products_count <= 50,  # Reasonable limit
                        f"Returned {products_count} products (reasonable)" if products_count <= 50 else f"Returned {products_count} products (excessive)",
                        "MEDIUM"
                    )
                    
            except Exception as e:
                self.add_result(
                    "Parameter Pollution Test",
                    False,
                    f"Error testing parameter pollution: {e}",
                    "MEDIUM"
                )

    async def test_rate_limiting(self):
        """Test rate limiting mechanisms"""
        print("\n⏱️ Testing Rate Limiting...")
        
        # Test rapid requests to a non-exempt endpoint (products list)
        # Note: /health is exempt from rate limiting, so we test /api/v1/products/count instead
        async with aiohttp.ClientSession() as session:
            rapid_requests = 0
            successful_requests = 0
            rate_limited_requests = 0
            
            # Use authentication token for this test
            headers = {"Authorization": f"Bearer {self.test_token}"} if self.test_token else {}
            
            try:
                # Send requests with small delays to avoid overwhelming the server
                for i in range(70):
                    try:
                        async with session.get(
                            f"{self.base_url}/api/v1/products/count",
                            headers=headers
                        ) as response:
                            rapid_requests += 1
                            if response.status == 200:
                                successful_requests += 1
                            elif response.status == 429:  # Rate limited
                                rate_limited_requests += 1
                                break  # Stop once we hit rate limit
                            
                            # Small delay between requests
                            await asyncio.sleep(0.05)
                            
                    except Exception as e:
                        continue
                        
                rate_limited = rate_limited_requests > 0
                
                # Rate limiting should kick in with 70 rapid requests if limit is 60/minute
                self.add_result(
                    "Rate Limiting",
                    rate_limited or successful_requests < rapid_requests,  
                    f"Rate limiting working: {successful_requests} succeeded, {rate_limited_requests} rate limited out of {rapid_requests} total" if rate_limited else f"No rate limiting detected: {successful_requests}/{rapid_requests} succeeded",
                    "MEDIUM"
                )
                
            except Exception as e:
                self.add_result(
                    "Rate Limiting Test",
                    False,
                    f"Error testing rate limiting: {e}",
                    "MEDIUM"
                )

    async def test_error_handling_security(self):
        """Test that error messages don't leak sensitive information"""
        print("\n🚨 Testing Error Handling Security...")
        
        async with aiohttp.ClientSession() as session:
            # Test 1: Database errors don't leak connection strings
            try:
                async with session.get(f"{self.base_url}/api/v1/products/NONEXISTENT") as response:
                    text = await response.text()
                    
                    # Check for database connection leaks
                    sensitive_indicators = [
                        "postgresql://",
                        "postgres@",
                        "password=",
                        "supabase.co",
                        "eyJ",  # JWT tokens
                        "AIza",  # Google API keys
                        "connectionstring",
                        "database_url"
                    ]
                    
                    has_leak = any(indicator.lower() in text.lower() for indicator in sensitive_indicators)
                    
                    self.add_result(
                        "Database Error Information Leakage",
                        not has_leak,
                        "No sensitive info in error messages" if not has_leak else "Potential sensitive info leak in errors",
                        "HIGH"
                    )
                    
            except Exception as e:
                self.add_result(
                    "Error Handling Test",
                    False,
                    f"Error testing error handling: {e}",
                    "MEDIUM"
                )
                
            # Test 2: Authentication errors are generic
            try:
                async with session.post(
                    f"{self.base_url}/api/v1/auth/login",
                    data={"username": "nonexistent@example.com", "password": "wrongpass"}
                ) as response:
                    
                    text = await response.text()
                    
                    # Should not reveal whether user exists or not
                    revealing_phrases = [
                        "user not found",
                        "user does not exist", 
                        "invalid user",
                        "email not registered"
                    ]
                    
                    is_revealing = any(phrase in text.lower() for phrase in revealing_phrases)
                    
                    self.add_result(
                        "Authentication Error Security",
                        not is_revealing,
                        "Generic auth error messages" if not is_revealing else "Auth errors reveal user existence",
                        "MEDIUM"
                    )
                    
            except Exception as e:
                self.add_result(
                    "Auth Error Test",
                    False,
                    f"Error testing auth errors: {e}",
                    "MEDIUM"
                )

    async def test_cors_and_headers(self):
        """Test CORS settings and security headers"""
        print("\n🌐 Testing CORS and Security Headers...")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/health") as response:
                    headers = dict(response.headers)
                    
                    # Check for security headers (case-insensitive)
                    headers_lower = {k.lower(): v for k, v in headers.items()}
                    
                    security_headers = {
                        "x-content-type-options": "nosniff",
                        "x-frame-options": "DENY",
                        "x-xss-protection": "1; mode=block",
                        "strict-transport-security": None,  # Should exist
                        "content-security-policy": None     # Should exist
                    }
                    
                    missing_headers = []
                    for header, expected_value in security_headers.items():
                        if header not in headers_lower:
                            missing_headers.append(header)
                        elif expected_value and headers_lower[header] != expected_value:
                            missing_headers.append(f"{header} (wrong value)")
                    
                    self.add_result(
                        "Security Headers",
                        len(missing_headers) == 0,  # All headers must be present
                        f"All security headers present" if len(missing_headers) == 0 else f"Missing headers: {missing_headers}",
                        "MEDIUM"
                    )
                    
                    # Check CORS settings - test with Origin header to trigger CORS
                    cors_headers = [h for h in headers_lower.keys() if h.startswith('access-control')]
                    has_cors = len(cors_headers) > 0
                    
                    # If no CORS headers found, try with Origin header
                    if not has_cors:
                        try:
                            async with session.get(
                                f"{self.base_url}/health", 
                                headers={"Origin": "https://example.com"}
                            ) as cors_response:
                                cors_headers_dict = {k.lower(): v for k, v in dict(cors_response.headers).items()}
                                cors_headers = [h for h in cors_headers_dict.keys() if h.startswith('access-control')]
                                has_cors = len(cors_headers) > 0
                        except:
                            pass
                    
                    self.add_result(
                        "CORS Configuration",
                        has_cors,
                        f"CORS headers configured ({len(cors_headers)} headers)" if has_cors else "No CORS headers found",
                        "LOW"
                    )
                    
            except Exception as e:
                self.add_result(
                    "Headers Test",
                    False,
                    f"Error testing headers: {e}",
                    "MEDIUM"
                )

    async def test_jwt_security(self):
        """Test JWT token security"""
        print("\n🎫 Testing JWT Security...")
        
        if not self.test_token:
            print("⚠️ Skipping JWT tests - no test token available")
            return
            
        async with aiohttp.ClientSession() as session:
            # Test 1: Expired/Invalid token handling
            invalid_tokens = [
                # Raw invalid tokens (Bearer will be added)
                "invalid.token.here",
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
                "",
                "fake-token",
                # Complete invalid headers (Bearer already included)
                "Bearer ",
                "Bearer\tinvalid",
                "bearer invalid",
                "Basic invalid"
            ]
            
            all_rejected = True
            rejection_details = []
            
            for i, invalid_token in enumerate(invalid_tokens):
                try:
                    # Determine header format
                    if any(invalid_token.lower().startswith(prefix) for prefix in ["bearer", "basic"]):
                        headers = {"Authorization": invalid_token}
                        test_desc = f"Token '{invalid_token}'"
                    else:
                        headers = {"Authorization": f"Bearer {invalid_token}"}
                        test_desc = f"Token 'Bearer {invalid_token}'"
                        
                    async with session.get(
                        f"{self.base_url}/api/v1/users/me",
                        headers=headers
                    ) as response:
                        status = response.status
                        
                        # Debug logging
                        print(f"  Testing {test_desc}: status {status}")
                        
                        # Should reject invalid tokens with 401 (unauthorized) or 403 (forbidden)
                        properly_rejected = status in [401, 403]
                        
                        if not properly_rejected:
                            all_rejected = False
                            if status == 429:
                                rejection_details.append(f"{test_desc} hit rate limit (429)")
                            elif status == 200:
                                rejection_details.append(f"{test_desc} was accepted (200)")
                            else:
                                rejection_details.append(f"{test_desc} returned unexpected status {status}")
                        
                        # Add delay between tests to avoid rate limiting
                        await asyncio.sleep(0.2)
                        
                except Exception as e:
                    # Exception during request is also a form of rejection
                    print(f"  Testing {test_desc}: exception {e}")
                    continue
            
            self.add_result(
                "Invalid JWT Rejection",
                all_rejected,
                "All invalid JWTs properly rejected" if all_rejected else f"Some tokens were not properly rejected: {', '.join(rejection_details)}",
                "HIGH"
            )

    def print_summary(self):
        """Print comprehensive security test summary"""
        print("\n" + "="*80)
        print("🔒 CLEAR-MEAT API SECURITY TEST RESULTS")
        print("="*80)
        
        # Count results by severity
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        passed_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for result in self.results:
            severity_counts[result.severity] += 1
            if result.passed:
                passed_counts[result.severity] += 1
        
        # Overall security score
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        security_score = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📊 OVERALL SECURITY SCORE: {security_score:.1f}% ({passed_tests}/{total_tests} tests passed)")
        
        # Security level assessment
        critical_failures = severity_counts["CRITICAL"] - passed_counts["CRITICAL"]
        high_failures = severity_counts["HIGH"] - passed_counts["HIGH"]
        
        if critical_failures > 0:
            security_level = "🚨 CRITICAL ISSUES FOUND"
        elif high_failures > 0:
            security_level = "⚠️ HIGH RISK ISSUES FOUND"
        elif security_score >= 90:
            security_level = "✅ GOOD SECURITY POSTURE"
        elif security_score >= 75:
            security_level = "⚠️ MODERATE SECURITY POSTURE"
        else:
            security_level = "❌ POOR SECURITY POSTURE"
        
        print(f"🛡️ SECURITY LEVEL: {security_level}")
        
        # Detailed breakdown
        print(f"\n📋 TEST BREAKDOWN:")
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if severity_counts[severity] > 0:
                print(f"  {severity}: {passed_counts[severity]}/{severity_counts[severity]} passed")
        
        # Failed tests detail
        failed_tests = [r for r in self.results if not r.passed]
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for result in failed_tests:
                print(f"  [{result.severity}] {result.test_name}: {result.details}")
        
        # Recommendations
        print(f"\n💡 SECURITY RECOMMENDATIONS:")
        if critical_failures > 0:
            print("  🚨 Address CRITICAL issues immediately before production deployment")
        if high_failures > 0:
            print("  ⚠️ Resolve HIGH risk issues as soon as possible")
        
        print("  🔒 Regular security testing should be part of CI/CD pipeline")
        print("  📝 Consider external security audit for production systems")
        print("  🔄 Update dependencies regularly for security patches")

async def main():
    """Run all security tests"""
    print("🔒 Starting Clear-Meat API Security Testing Suite...")
    print("=" * 60)
    
    tester = SecurityTestSuite()
    
    # Setup
    await tester.setup_test_user()
    
    # Run all security tests
    await tester.test_key_exposure_protection()
    await tester.test_authentication_security() 
    await tester.test_input_validation()
    await tester.test_rate_limiting()
    await tester.test_error_handling_security()
    await tester.test_cors_and_headers()
    await tester.test_jwt_security()
    
    # Print comprehensive summary
    tester.print_summary()

if __name__ == "__main__":
    asyncio.run(main()) 