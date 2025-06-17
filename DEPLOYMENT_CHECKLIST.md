# Deployment Readiness Checklist

## 🚨 Critical Issues to Fix Before Deployment

### 1. **Remove Hardcoded Credentials** (CRITICAL)
- [ ] Fix hardcoded database URLs in:
  - `app/db/session.py:17` 
  - `app/db/connection.py:35`
  - `create_tables.py`
  - `scripts/switch_env.py`
- [ ] Replace with environment variable without fallback for production

### 2. **Replace Print Statements** (HIGH)
- [ ] 556 print() statements need to be replaced with proper logging
- [ ] Use `logger.info()`, `logger.debug()`, `logger.error()` instead

### 3. **Fix CORS Configuration** (CRITICAL)
- [ ] Remove wildcard CORS fallback in `app/main.py:78`
- [ ] Require explicit origins in production

### 4. **Logging Configuration** (HIGH)
- [ ] Disable debug logging in production
- [ ] Set up centralized logging configuration
- [ ] Remove or guard all DEBUG statements

### 5. **Environment Variables** (CRITICAL)
Required for production:
```bash
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=[32+ character secret - REQUIRED]
DATABASE_URL=[production database URL with SSL]
SUPABASE_URL=[production Supabase URL]
SUPABASE_KEY=[production Supabase key]
SUPABASE_SERVICE_KEY=[service role key]
GEMINI_API_KEY=[API key]
REDIS_URL=[Redis URL for caching/rate limiting]
BACKEND_CORS_ORIGINS=[comma-separated allowed origins]
RATE_LIMIT_PER_MINUTE=120
```

### 6. **Security Audit Commands**
Run these before deployment:
```bash
# Find any remaining credentials
grep -r "password\|secret\|key\|token" --include="*.py" . | grep -v "os.environ"

# Find localhost references
grep -r "localhost\|127\.0\.0\.1" --include="*.py" .

# Find print statements
grep -r "print(" --include="*.py" .

# Find debug code
grep -r "DEBUG\|debug" --include="*.py" .
```

## ✅ Good Practices Already in Place

1. **Environment Configuration**
   - Settings validation
   - Auth bypass protection in production
   - Environment-based configuration

2. **Security**
   - JWT implementation
   - Rate limiting with Redis
   - Security headers (CSP, HSTS, etc.)
   - Path traversal protection

3. **Health Checks**
   - `/health` - Basic health check
   - `/health/db` - Database connectivity
   - `/health/supabase` - Supabase connectivity

4. **Database**
   - Connection pooling
   - SSL configuration for production
   - Retry mechanisms

## 📋 Pre-Deployment Steps

1. **Fix all critical issues above**
2. **Run tests**:
   ```bash
   pytest tests/
   ```
3. **Check environment variables**:
   ```bash
   python scripts/maintenance/check_credentials.py
   ```
4. **Verify no secrets in code**:
   ```bash
   git secrets --scan
   ```

## 🚀 Deployment Configuration

### Docker Production Build
```dockerfile
FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV DEBUG=false
# ... rest of Dockerfile
```

### Recommended Production Setup
- Use environment variable management service (AWS Secrets Manager, etc.)
- Enable application monitoring (Sentry, DataDog, etc.)
- Set up centralized logging (CloudWatch, ELK stack, etc.)
- Configure autoscaling based on health checks
- Enable SSL/TLS termination at load balancer

## ⚠️ Post-Deployment Monitoring

1. Monitor error rates
2. Track API response times
3. Monitor rate limit hits
4. Check database connection pool usage
5. Monitor memory and CPU usage

## 🔒 Security Recommendations

1. Rotate SECRET_KEY regularly
2. Use separate database users for read/write operations
3. Enable database SSL enforcement
4. Implement API versioning
5. Add request ID tracking for debugging
6. Consider adding OWASP security headers