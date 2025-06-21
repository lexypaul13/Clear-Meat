# 🧪 Clear-Meat API Testing Suite

## Deployment Verification Tests

This directory contains comprehensive tests to verify that all endpoints work correctly before deployment.

## 🚀 Quick Start

### Option 1: Simple Script (Recommended)
```bash
# Test local development server
./test_deployment.sh

# Test specific URL
./test_deployment.sh --url http://localhost:8000

# Test production server
./test_deployment.sh --url https://api.yourdomain.com

# Verbose output
./test_deployment.sh --verbose
```

### Option 2: Direct Python Script
```bash
# Basic test
python3 tests/deployment_verification_test.py

# Test specific URL
python3 tests/deployment_verification_test.py --url http://localhost:8000

# Verbose output
python3 tests/deployment_verification_test.py --verbose
```

## 📋 What Gets Tested

### 1. **Basic Health Checks**
- ✅ `/health` - API health status
- ✅ Response time measurement
- ✅ JSON response validation

### 2. **API Documentation**
- ✅ `/docs` - OpenAPI documentation
- ✅ `/redoc` - ReDoc documentation  
- ✅ `/openapi.json` - OpenAPI schema

### 3. **Product Endpoints**
- ✅ `/api/v1/products/count` - Product count
- ✅ `/api/v1/products/` - Product listing with pagination
- ✅ `/api/v1/products/{code}` - Individual product details
- ✅ `/api/v1/products/{code}/health-assessment` - Health assessments

### 4. **Search Functionality**
- ✅ `/api/v1/products/search` - Product search
- ✅ Multiple search terms (bacon, chicken, beef)
- ✅ Result validation

### 5. **Performance Monitoring**
- ✅ `/api/v1/performance/metrics` - Performance metrics
- ✅ Uptime tracking
- ✅ Response time analysis

### 6. **Error Handling**
- ✅ 404 responses for invalid products
- ✅ 404 responses for invalid endpoints
- ✅ Proper error message formatting

### 7. **Security & Configuration**
- ✅ CORS headers verification
- ✅ Rate limiting behavior
- ✅ HTTP response codes

## 📊 Test Output Example

```
🚀 Starting Clear-Meat API Deployment Verification Tests
📍 Testing against: http://localhost:8000
======================================================================

🧪 Running Basic Health Check tests...
✅ Health Check: PASS (45.2ms)

🧪 Running API Documentation tests...
✅ OpenAPI Docs: PASS (123.4ms)
✅ ReDoc Documentation: PASS (89.1ms)
✅ OpenAPI Schema: PASS (67.8ms)

🧪 Running Product Endpoints tests...
✅ Product Count: PASS (234.5ms) - Total products: 1,247
✅ Products List: PASS (156.7ms) - Retrieved 5 products
✅ Product Info: PASS (98.3ms) - Product: Oscar Mayer Turkey Bacon
✅ Health Assessment: PASS (2,456.1ms) - Summary: This product contains several concerning...

======================================================================
📊 DEPLOYMENT VERIFICATION TEST REPORT
======================================================================
✅ Passed: 15
❌ Failed: 0
📈 Success Rate: 15/15 (100.0%)
⚡ Average Response Time: 234.2ms

🎉 ALL TESTS PASSED - API IS READY FOR DEPLOYMENT! 🚀
```

## 🔧 Prerequisites

### Required Dependencies
```bash
# Install required Python packages
pip install requests

# Or if using requirements.txt
pip install -r requirements.txt
```

### Required Services
- Clear-Meat API running and accessible
- Database with sample data
- Internet connection for external API tests (citations)

## 🐳 Testing with Docker

### Test Docker Compose Setup
```bash
# Start services
docker-compose up -d

# Wait for services to be ready
sleep 30

# Run tests
./test_deployment.sh --url http://localhost:8000

# Clean up
docker-compose down
```

### Test Production Docker
```bash
# Build production image
docker build -t clear-meat-api .

# Run with production environment
docker run -d -p 8000:8000 \
  -e DATABASE_URL="your-production-db-url" \
  -e ENVIRONMENT=production \
  clear-meat-api

# Test
./test_deployment.sh --url http://localhost:8000
```

## 🎯 Test Scenarios

### Local Development
```bash
# Start development server
uvicorn app.main:app --reload

# Run tests
./test_deployment.sh
```

### Staging Environment
```bash
./test_deployment.sh --url https://staging-api.yourdomain.com
```

### Production Environment
```bash
./test_deployment.sh --url https://api.yourdomain.com
```

## 📈 Performance Expectations

### Response Time Benchmarks
- **Health check**: < 100ms
- **Product list**: < 500ms
- **Individual product**: < 200ms
- **Health assessment**: < 3000ms (includes AI processing)
- **Search queries**: < 800ms

### Success Criteria
- ✅ **100% endpoint availability**
- ✅ **All response codes correct**
- ✅ **JSON responses valid**
- ✅ **Average response time < 1000ms**
- ✅ **No unhandled exceptions**

## 🐛 Troubleshooting

### Common Issues

#### "API is not reachable"
```bash
# Check if API is running
curl http://localhost:8000/health

# Check Docker services
docker-compose ps

# Check logs
docker-compose logs api
```

#### "Database connection failed"
```bash
# Check database status
docker-compose logs supabase-db

# Verify environment variables
echo $DATABASE_URL

# Test database connection
python3 -c "from app.db.connection import engine; print(engine.execute('SELECT 1').scalar())"
```

#### "Health assessment tests failing"
- Check Gemini API key configuration
- Verify internet connectivity
- Check if test products have ingredients data

#### "Citation tests timing out"
- External citation APIs may be slow or rate-limited
- Tests will pass with warnings for network issues
- Ensure stable internet connection

### Debug Mode
```bash
# Enable verbose logging
./test_deployment.sh --verbose

# Check specific endpoint manually
curl -v http://localhost:8000/api/v1/products/count
```

## 🔄 Continuous Integration

### GitHub Actions Example
```yaml
name: Deployment Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start services
        run: docker-compose up -d
      - name: Wait for services
        run: sleep 30
      - name: Run deployment tests
        run: ./test_deployment.sh --url http://localhost:8000
      - name: Cleanup
        run: docker-compose down
```

## 📝 Adding New Tests

To add tests for new endpoints:

1. **Add test method to `DeploymentTestSuite`**:
```python
def test_new_feature(self) -> bool:
    """Test new feature endpoint."""
    success, response, error = self.make_request('GET', '/api/v1/new-feature')
    
    if success and response.status_code == 200:
        self.log_test_result("New Feature", True, "Feature works", response.elapsed.total_seconds())
        return True
    else:
        self.log_test_result("New Feature", False, f"HTTP {response.status_code}")
        return False
```

2. **Add to test suite**:
```python
test_functions = [
    # ... existing tests ...
    ("New Feature", self.test_new_feature),
]
```

## 🚀 Deployment Checklist

Before deploying to production:

- [ ] All tests pass locally
- [ ] All tests pass in staging environment
- [ ] Performance benchmarks met
- [ ] Security configurations verified
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] External API keys configured
- [ ] Monitoring and alerting set up

**Only deploy when all tests pass!** ✅