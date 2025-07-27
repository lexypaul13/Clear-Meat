# Authentication Fix Deployment Guide

## Summary of Fixes

We've fixed the critical authentication issue that was causing 401 errors for all API calls after login.

### Root Cause
Line 258 in `app/internal/dependencies.py` was using a non-existent `supabase_service.query()` method:
```python
# BROKEN CODE:
user = supabase_service.query(db_models.User).filter(db_models.User.id == payload["sub"]).first()
```

### Fix Applied
Replaced with the correct Supabase client query:
```python
# FIXED CODE:
client = supabase_service.get_client()
result = client.table('profiles').select('*').eq('id', payload['sub']).execute()
```

## Deployment Steps

### 1. Apply Database Migrations

Run these migrations in your Supabase SQL editor:

```sql
-- First, apply the profiles INSERT policy fix
-- File: migrations/fix_profiles_insert_policy.sql
```

This adds INSERT policies for the profiles table to allow user registration.

### 2. Deploy Code Changes

The fixed file is: `app/internal/dependencies.py`

Deploy to Railway:
```bash
git add app/internal/dependencies.py
git commit -m "Fix authentication: Replace non-existent query method with correct Supabase client calls"
git push origin main
```

### 3. Test Authentication

Run the test script locally first:
```bash
python scripts/test_authentication_fix.py
```

Expected output:
```
✅ Registration successful!
✅ Protected endpoint access successful!
✅ Login successful!
✅ Protected endpoint access with login token successful!
✅ ALL AUTHENTICATION TESTS PASSED!
```

### 4. Test with iOS App

1. Force logout in the iOS app
2. Login with existing credentials
3. Navigate to Settings - should show real user data (not "Guest User")
4. Navigate to Explore - recommendations should load

### 5. Quick Verification Commands

```bash
# Test login
curl -X POST https://clear-meat-api-production.up.railway.app/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=password"

# Test protected endpoint (use token from login)
curl -H "Authorization: Bearer <token>" \
  https://clear-meat-api-production.up.railway.app/api/v1/users/me
```

## What Was Fixed

1. **JWT Token Validation**: Fixed the user lookup query for legacy tokens
2. **Database Query Method**: Replaced SQLAlchemy-style query with Supabase client table query
3. **User Object Creation**: Properly creates user objects from profiles table data
4. **RLS Policies**: Added INSERT policies for profiles table

## Monitoring

After deployment, monitor:
- Railway logs for any JWT validation errors
- Supabase logs for database query failures
- iOS app crash reports related to authentication

## Rollback Plan

If issues persist:
1. Revert the code changes
2. Add temporary logging to identify the exact failure point
3. Consider enabling `ENABLE_AUTH_BYPASS=true` temporarily (NEVER in production)

## Success Criteria

- [ ] No more 401 errors after successful login
- [ ] Settings shows actual user data
- [ ] Explore tab loads recommendations
- [ ] All protected endpoints work with valid tokens 