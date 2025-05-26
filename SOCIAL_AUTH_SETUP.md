# 🔐 **Social Authentication Setup Guide**

This guide explains how to set up social authentication for the MeatWise API using **Supabase's built-in OAuth providers**. Supabase handles all the OAuth complexity for you!

## 📋 **Overview**

The MeatWise API supports the following authentication methods:
- **Google OAuth** - Sign in with Google account
- **Facebook OAuth** - Sign in with Facebook account  
- **Apple OAuth** - Sign in with Apple ID
- **Twitter/X OAuth** - Sign in with Twitter/X account
- **Phone/SMS** - Sign in with phone number and OTP

## 🚀 **Quick Setup**

### **1. Configure OAuth Providers in Supabase Dashboard**

Instead of manually creating OAuth apps, use Supabase's streamlined setup:

1. **Go to your Supabase Dashboard** → Authentication → Providers
2. **Enable the providers** you want to use
3. **Add your OAuth credentials** (client ID and secret)
4. **Set redirect URLs** to your Supabase project URL

### **2. Environment Variables**

Add these to your `.env` file:

```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# OAuth Provider Credentials (set in Supabase Dashboard)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

FACEBOOK_CLIENT_ID=your_facebook_app_id
FACEBOOK_CLIENT_SECRET=your_facebook_app_secret

APPLE_CLIENT_ID=your_apple_client_id
SUPABASE_AUTH_EXTERNAL_APPLE_SECRET=your_apple_client_secret

TWITTER_CLIENT_ID=your_twitter_client_id
TWITTER_CLIENT_SECRET=your_twitter_client_secret

# SMS Provider (optional - for phone auth)
SUPABASE_AUTH_SMS_TWILIO_AUTH_TOKEN=your_twilio_auth_token
```

## 🔧 **Provider-Specific Setup**

### **Google OAuth**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `https://your-project.supabase.co/auth/v1/callback`

### **Facebook OAuth**
1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create a new app
3. Add Facebook Login product
4. Set Valid OAuth Redirect URIs: `https://your-project.supabase.co/auth/v1/callback`

### **Apple OAuth**
1. Go to [Apple Developer](https://developer.apple.com/)
2. Create a new App ID and Service ID
3. Configure Sign in with Apple
4. Add return URL: `https://your-project.supabase.co/auth/v1/callback`

### **Twitter/X OAuth**
1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Create a new app
3. Enable OAuth 2.0
4. Add callback URL: `https://your-project.supabase.co/auth/v1/callback`

## 📱 **Frontend Integration**

### **Web (JavaScript)**

```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'your-supabase-url',
  'your-supabase-anon-key'
)

// OAuth Sign In
async function signInWithProvider(provider) {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: provider, // 'google', 'facebook', 'apple', 'twitter'
    options: {
      redirectTo: 'http://localhost:3000/auth/callback'
    }
  })
  
  if (error) console.error('Error:', error)
  return data
}

// Phone/SMS Sign In
async function signInWithPhone(phone) {
  const { data, error } = await supabase.auth.signInWithOtp({
    phone: phone
  })
  
  if (error) console.error('Error:', error)
  return data
}

// Verify Phone OTP
async function verifyOTP(phone, token) {
  const { data, error } = await supabase.auth.verifyOtp({
    phone: phone,
    token: token,
    type: 'sms'
  })
  
  if (error) console.error('Error:', error)
  return data
}
```

### **React Native**

```javascript
import { createClient } from '@supabase/supabase-js'
import { makeRedirectUri } from 'expo-auth-session'

const supabase = createClient(
  'your-supabase-url',
  'your-supabase-anon-key'
)

// OAuth Sign In
async function signInWithProvider(provider) {
  const redirectTo = makeRedirectUri({
    path: '/auth/callback',
  })

  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: provider,
    options: {
      redirectTo,
      skipBrowserRedirect: true,
    },
  })

  if (error) console.error('Error:', error)
  return data
}
```

## 🔗 **API Endpoints**

### **Get Available Providers**
```http
GET /api/v1/auth/providers
```

Response:
```json
{
  "providers": {
    "google": {
      "name": "Google",
      "icon": "google",
      "color": "#4285f4",
      "enabled": true,
      "auth_url": "https://your-project.supabase.co/auth/v1/authorize?provider=google"
    },
    "facebook": {
      "name": "Facebook",
      "icon": "facebook", 
      "color": "#1877f2",
      "enabled": true,
      "auth_url": "https://your-project.supabase.co/auth/v1/authorize?provider=facebook"
    }
  },
  "phone_auth_enabled": true,
  "email_auth_enabled": true
}
```

### **Initiate OAuth**
```http
GET /api/v1/auth/oauth/{provider}?redirect_url=http://localhost:3000/callback
```

### **Send Phone OTP**
```http
POST /api/v1/auth/phone/send-otp
Content-Type: application/json

{
  "phone": "+1234567890"
}
```

### **Verify Phone OTP**
```http
POST /api/v1/auth/phone/verify
Content-Type: application/json

{
  "phone": "+1234567890",
  "token": "123456"
}
```

## 🛡️ **Security Features**

### **Built-in by Supabase:**
- ✅ **CSRF Protection** - Automatic state parameter handling
- ✅ **Rate Limiting** - Configurable limits for auth attempts
- ✅ **JWT Tokens** - Secure, stateless authentication
- ✅ **Refresh Tokens** - Automatic token rotation
- ✅ **Email Verification** - Optional email confirmation
- ✅ **Phone Verification** - OTP-based phone confirmation

### **Configuration:**
```toml
# In supabase/config.toml
[auth.rate_limit]
email_sent = 2
sms_sent = 30
sign_in_sign_ups = 30
token_verifications = 30
```

## 🧪 **Testing**

### **Local Development**
1. Start Supabase locally: `supabase start`
2. Use test OAuth credentials in development
3. Test with local redirect URLs

### **Phone Auth Testing**
```toml
# Add to supabase/config.toml for testing
[auth.sms.test_otp]
4152127777 = "123456"
```

## 🚨 **Troubleshooting**

### **Common Issues:**

**OAuth redirect mismatch:**
- Ensure redirect URIs match exactly in provider settings
- Check Supabase project URL is correct

**Phone OTP not received:**
- Verify phone number format (+1234567890)
- Check Twilio configuration if using custom SMS provider
- Use test OTP for development

**Token validation errors:**
- Verify JWT secret configuration
- Check token expiry settings
- Ensure proper CORS configuration

### **Debug Mode:**
```bash
# Enable debug logging
export SUPABASE_DEBUG=true
```

## 📚 **Additional Resources**

- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [OAuth Provider Setup Guides](https://supabase.com/docs/guides/auth/social-login)
- [Phone Auth Guide](https://supabase.com/docs/guides/auth/phone-login)
- [JWT Configuration](https://supabase.com/docs/guides/auth/jwt)

---

## 🎯 **Benefits of Supabase Built-in Auth**

✅ **Simplified Setup** - No manual OAuth app configuration  
✅ **Automatic Handling** - Supabase manages OAuth flows  
✅ **Built-in Security** - CSRF, rate limiting, token management  
✅ **Easy Integration** - Works seamlessly with Supabase client libraries  
✅ **Scalable** - Handles high-volume authentication out of the box 