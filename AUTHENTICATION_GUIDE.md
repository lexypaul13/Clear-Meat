# 🔐 Clear-Meat API Authentication Guide

## Overview

The Clear-Meat API uses **Supabase Authentication** with JWT tokens for user management and API access. This guide shows you how to sign up, login, and access protected endpoints.

## 🚀 Quick Start

### 1. Sign Up for a New Account

**Endpoint:** `POST /api/v1/auth/register`

**Request Body:**
```json
{
  "email": "your-email@example.com",
  "password": "YourSecurePassword123!",
  "full_name": "Your Full Name"
}
```

**Password Requirements:**
- Minimum 8 characters
- Must contain at least 3 of: uppercase letter, lowercase letter, number, special character
- Cannot be a common weak password

**Example with curl:**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe"
  }'
```

**Successful Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Login with Existing Account

**Endpoint:** `POST /api/v1/auth/login`

**Request Body (Form Data):**
```
username=your-email@example.com
password=YourSecurePassword123!
```

**Example with curl:**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john.doe@example.com&password=SecurePass123!"
```

**Successful Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Using Your Access Token

Include the access token in the `Authorization` header for protected endpoints:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://127.0.0.1:8000/api/v1/products/count
```

## 🛡️ Security Features

### Password Validation
- ✅ Minimum 8 characters, maximum 128 characters
- ✅ Complexity requirements (3 of 4: uppercase, lowercase, number, special char)
- ✅ Blocks common weak passwords
- ✅ Server-side validation with detailed error messages

### Rate Limiting
- ✅ 10 requests per minute per IP for authentication endpoints
- ✅ Protection against brute force attacks
- ✅ Configurable rate limits

### JWT Token Security
- ✅ Tokens expire after 24 hours
- ✅ Secure token generation using Supabase
- ✅ Bearer token authentication

## 📋 Complete Examples

### Python Example

```python
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

# 1. Sign up
def sign_up(email, password, full_name):
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": password,
        "full_name": full_name
    })
    
    if response.status_code == 200:
        data = response.json()
        return data["access_token"]
    else:
        print("Signup failed:", response.json())
        return None

# 2. Login
def login(email, password):
    response = requests.post(f"{BASE_URL}/auth/login", data={
        "username": email,
        "password": password
    })
    
    if response.status_code == 200:
        data = response.json()
        return data["access_token"]
    else:
        print("Login failed:", response.json())
        return None

# 3. Use protected endpoint
def get_product_count(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/products/count", headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print("API call failed:", response.json())
        return None

# Usage
email = "test@example.com"
password = "SecurePassword123!"
name = "Test User"

# Register or login
token = sign_up(email, password, name)
if not token:
    token = login(email, password)

if token:
    # Use the API
    result = get_product_count(token)
    print("Product count:", result)
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

const BASE_URL = 'http://127.0.0.1:8000/api/v1';

// Sign up
async function signUp(email, password, fullName) {
  try {
    const response = await axios.post(`${BASE_URL}/auth/register`, {
      email,
      password,
      full_name: fullName
    });
    
    return response.data.access_token;
  } catch (error) {
    console.error('Signup failed:', error.response.data);
    return null;
  }
}

// Login
async function login(email, password) {
  try {
    const response = await axios.post(`${BASE_URL}/auth/login`, 
      `username=${email}&password=${password}`,
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      }
    );
    
    return response.data.access_token;
  } catch (error) {
    console.error('Login failed:', error.response.data);
    return null;
  }
}

// Use protected endpoint
async function getProductCount(token) {
  try {
    const response = await axios.get(`${BASE_URL}/products/count`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('API call failed:', error.response.data);
    return null;
  }
}

// Usage
async function main() {
  const email = 'test@example.com';
  const password = 'SecurePassword123!';
  const name = 'Test User';
  
  // Register or login
  let token = await signUp(email, password, name);
  if (!token) {
    token = await login(email, password);
  }
  
  if (token) {
    // Use the API
    const result = await getProductCount(token);
    console.log('Product count:', result);
  }
}

main();
```

## 🔧 Configuration

### Environment Variables

The server requires these environment variables for authentication:

```bash
# Supabase Configuration
SUPABASE_URL=https://ksgxendfsejkxhrmfsbi.supabase.co
SUPABASE_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_role_key_here

# Security
SECRET_KEY=your_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours

# Development only - never use in production
ENABLE_AUTH_BYPASS=false
```

### Development Mode

For development testing, you can enable auth bypass:

```bash
ENABLE_AUTH_BYPASS=true python3 -m uvicorn app.main:app --port 8000
```

**⚠️ Warning:** Never enable auth bypass in production!

## 🚨 Error Handling

### Common Errors

**400 Bad Request - Weak Password:**
```json
{
  "detail": "Password must contain at least 3 of: uppercase letter, lowercase letter, number, special character"
}
```

**409 Conflict - User Exists:**
```json
{
  "detail": "A user with this email address already exists. Please login or use a different email."
}
```

**401 Unauthorized - Invalid Credentials:**
```json
{
  "detail": "Authentication failed: Invalid login credentials"
}
```

**401 Unauthorized - Invalid Token:**
```json
{
  "detail": "Invalid token"
}
```

**429 Too Many Requests - Rate Limited:**
```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

## ✅ Testing Your Setup

Run the authentication test script:

```bash
python3 auth_demo.py
```

This will:
1. ✅ Create a new test account
2. ✅ Login with the credentials
3. ✅ Test token generation
4. ⚠️ Show current token validation status

## 🔗 Related Documentation

- [API README](API_README.md) - Complete API documentation
- [Security Features](SECURITY_FIXES_APPLIED.md) - Security implementation details
- [Deployment Guide](DEPLOYMENT_CHECKLIST.md) - Production deployment instructions

## 🆘 Support

If you encounter issues:

1. Check server logs for detailed error messages
2. Verify environment variables are set correctly
3. Ensure Supabase credentials are valid
4. Test with the provided demo scripts

---

**Authentication Status:** ✅ **WORKING**
- User registration: ✅ Functional
- User login: ✅ Functional  
- Token generation: ✅ Functional
- Security validation: ✅ Functional 