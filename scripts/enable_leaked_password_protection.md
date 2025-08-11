# Enable Leaked Password Protection in Supabase

## Steps to Enable via Supabase Dashboard

1. **Navigate to Auth Settings:**
   - Go to your Supabase Dashboard: https://supabase.com/dashboard/project/ksgxendfsejkxhrmfsbi
   - Click on "Authentication" in the left sidebar
   - Go to "Auth Settings" tab

2. **Enable Leaked Password Protection:**
   - Scroll down to the "Security" section
   - Find "Leaked Password Protection"
   - Toggle it ON ✅
   - This will check passwords against HaveIBeenPwned database

3. **Configure Password Requirements (Optional but Recommended):**
   While you're there, also consider:
   - Minimum password length: Set to at least 8 characters
   - Password complexity requirements
   - Enable "Require email confirmation" for new signups

4. **Save Changes:**
   - Click "Save" button at the bottom of the page
   - Changes take effect immediately

## Alternative: Using Supabase CLI

```bash
# If you prefer to use the CLI (requires supabase CLI installed)
supabase --project-ref ksgxendfsejkxhrmfsbi auth set --enable-pwned-check=true
```

## Verification

After enabling, test with a known compromised password:
- Try registering with password "password123" 
- Should be rejected with message about compromised password

## Benefits

✅ Prevents users from using passwords that appear in data breaches
✅ Reduces account takeover risks
✅ No performance impact (checks are async)
✅ Free feature included with Supabase

## Notes

- This feature uses k-anonymity to protect user privacy
- Only a partial hash is sent to HaveIBeenPwned
- No full passwords leave your application
- Recommended by NIST guidelines