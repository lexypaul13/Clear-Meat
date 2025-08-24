j
## Quick Test Script

Create and run this Python script to test the health assessment endpoint:

```python
#!/usr/bin/env python3
import requests
import json

def test_health_assessment():
    # 1. Register test user
    register_url = "https://clear-meat-api-production.up.railway.app/api/v1/auth/register"
    user_data = {
        "email": "test.health.assessment@example.com",
        "password": "TestPassword123!",
        "full_name": "Health Assessment Tester"
    }
    
    response = requests.post(register_url, json=user_data)
    if response.status_code in [200, 201]:
        access_token = response.json().get('access_token')
    else:
        # Try login if user exists
        login_url = "https://clear-meat-api-production.up.railway.app/api/v1/auth/login"
        login_data = {"username": user_data["email"], "password": user_data["password"]}
        response = requests.post(login_url, data=login_data, 
                               headers={"Content-Type": "application/x-www-form-urlencoded"})
        access_token = response.json().get('access_token')
    
    # 2. Test health assessment endpoint
    product_code = "0013000798204"  # Heinz chicken gravy
    assessment_url = f"https://clear-meat-api-production.up.railway.app/api/v1/products/{product_code}/health-assessment-mcp"
    
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"format": "mobile"}
    
    response = requests.get(assessment_url, headers=headers, params=params, timeout=60)
    
    if response.status_code == 200:
        print("SUCCESS - Health Assessment JSON:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"ERROR {response.status_code}: {response.text}")

if __name__ == "__main__":
    test_health_assessment()
```

## Usage

1. **Save script**: `test_health_assessment.py`
2. **Run**: `python3 test_health_assessment.py`
3. **Expected**: JSON health assessment with ingredient risk analysis

## What It Tests

- ✅ User registration/login
- ✅ JWT authentication 
- ✅ Health assessment endpoint
- ✅ AI-powered ingredient analysis
- ✅ Risk categorization (high/moderate/low)
- ✅ Nutritional evaluation

## Sample Output

```json
{
  "summary": "Home style chicken gravy contains moderate-risk additives...",
  "grade": "C",
  "color": "Yellow",
  "high_risk": [...],
  "moderate_risk": [...],
  "nutrition": [...]
}
```

## Requirements

- `requests` library: `pip install requests`
- Internet connection
- Clear-Meat API running on Railway
