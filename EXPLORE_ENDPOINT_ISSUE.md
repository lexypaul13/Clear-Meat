# Explore Endpoint 500 Error - Final Issue

## Problem
The `/api/v1/users/explore` endpoint returns 500 Internal Server Error, preventing iOS app users from accessing the Explore tab with personalized recommendations.

## Current Status
✅ **Working**: Authentication, user registration, profile creation, sign in/out  
❌ **Broken**: Explore endpoint returning 500 error

## Root Cause
**Duplicate profile creation attempt** causing database constraint violation:
```
Failed to create user record: {'message': 'duplicate key value violates unique constraint "profiles_email_key"', 'code': '23505'}
```

## Technical Details

### Error Flow
1. User calls `/api/v1/users/explore`
2. Authentication dependency tries to create user profile 
3. Profile already exists from previous request
4. Database throws unique constraint violation
5. Error propagates to explore endpoint → 500 error

### Key Files
- **`app/internal/dependencies.py`** (lines 175-230): Profile creation logic
- **`app/api/v1/endpoints/users.py`** (line 695): Explore endpoint error handling
- **Database**: `profiles` table with unique constraint on `email`

### Error Log Pattern
```
User f2f13703-00fe-4f6e-b294-5b959a7f48b5 not found in local DB. Creating record.
HTTP Request: POST /rest/v1/profiles "HTTP/2 409 Conflict"
Failed to create user record: duplicate key value violates unique constraint "profiles_email_key"
Error in personalized explore
```

## Solution Needed
**Fix the profile creation logic** in `app/internal/dependencies.py` around line 175:

1. **Check if profile exists** before attempting INSERT
2. **Handle duplicate key errors gracefully** - return existing profile instead of failing
3. **Use UPSERT pattern** (INSERT ... ON CONFLICT DO NOTHING) if supported

## Expected Behavior
- First request: Creates profile successfully
- Subsequent requests: Uses existing profile without error
- Explore endpoint: Returns recommendations without 500 error
- iOS app: Explore tab loads properly

## Test Verification
After fix, this should work:
```bash
# Register user
curl -X POST https://clear-meat-api-production.up.railway.app/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","full_name":"Test User"}'

# Get token and test explore endpoint (should return 200, not 500)
curl -X GET https://clear-meat-api-production.up.railway.app/api/v1/users/explore \
  -H "Authorization: Bearer <token>"
```

## Impact
- **iOS App**: Explore tab will work
- **Dietary Preferences**: Can be tested once explore works
- **User Experience**: Complete app functionality restored 