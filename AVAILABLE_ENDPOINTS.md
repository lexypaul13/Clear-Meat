# 📋 Clear-Meat API - All Available Endpoints

## 🌐 Base URLs
- **Direct Railway API**: `https://clear-meat-api-production.up.railway.app`
- **Supabase Edge Function**: `https://ksgxendfsejkxhrmfsbi.supabase.co/functions/v1/clear-meat-api`

## 🏥 Health & Status Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `GET` | `/health` | Application health check | ✅ Working |
| `GET` | `/health/db` | Database connectivity check | ✅ Working |
| `GET` | `/health/supabase` | Supabase connection check | ✅ Working |

## 🔐 Authentication Endpoints

| Method | Endpoint | Description | Auth Required | Status |
|--------|----------|-------------|---------------|---------|
| `POST` | `/api/v1/auth/login` | Email/password login | ❌ | ✅ Working |
| `POST` | `/api/v1/auth/register` | User registration | ❌ | ✅ Working |

### Login Request Body:
```json
{
  "username": "user@example.com",
  "password": "your_password"
}
```

### Register Request Body:
```json
{
  "email": "user@example.com",
  "password": "your_password",
  "full_name": "Full Name"
}
```

## 🥩 Product Endpoints

| Method | Endpoint | Description | Auth Required | Status |
|--------|----------|-------------|---------------|---------|
| `GET` | `/api/v1/products/` | List all products with pagination | ❌ | ✅ Working |
| `GET` | `/api/v1/products/count` | Get total product count | 🔒 | ✅ Working |
| `GET` | `/api/v1/products/nlp-search` | Natural language product search | ❌ | ✅ Working |
| `GET` | `/api/v1/products/recommendations` | Get product recommendations | 🔒 | ⚠️ Requires auth |
| `GET` | `/api/v1/products/{code}` | Get specific product by barcode | ❌ | ✅ Working |
| `GET` | `/api/v1/products/{code}/alternatives` | Get product alternatives | ❌ | ⚠️ May have issues |
| `GET` | `/api/v1/products/{code}/health-assessment-mcp` | Evidence-based health assessment with real PubMed citations | 🔒 | ✅ Working |

### Query Parameters:

**Products List (`/api/v1/products/`):**
- `skip`: Number to skip (pagination)
- `limit`: Max results (default: 100)
- `risk_rating`: Filter by risk rating

**NLP Search (`/api/v1/products/nlp-search`):**
- `q`: Search query (required)
- `limit`: Max results (default: 20)
- `skip`: Number to skip

**Example:**
```
GET /api/v1/products/nlp-search?q=low sodium chicken&limit=10
```

## 👤 User Endpoints (All Require Authentication 🔒)

| Method | Endpoint | Description | Status |
|--------|----------|-------------|---------|
| `GET` | `/api/v1/users/me` | Get current user profile | 🔒 Auth required |
| `PUT` | `/api/v1/users/me` | Update user profile | 🔒 Auth required |
| `GET` | `/api/v1/users/history` | Get user scan history | 🔒 Auth required |
| `POST` | `/api/v1/users/history` | Add scan to history | 🔒 Auth required |
| `GET` | `/api/v1/users/favorites` | Get user favorites | 🔒 Auth required |
| `POST` | `/api/v1/users/favorites` | Add product to favorites | 🔒 Auth required |
| `DELETE` | `/api/v1/users/favorites/{product_code}` | Remove from favorites | 🔒 Auth required |
| `GET` | `/api/v1/users/recommendations` | Get personalized recommendations | 🔒 Auth required |
| `GET` | `/api/v1/users/explore` | Get explore page content | 🔒 Auth required |

## 🔒 Authentication

For endpoints marked with 🔒, include these headers:

**For Supabase Edge Function:**
```http
Authorization: Bearer [supabase_anon_key]
apikey: [supabase_anon_key]
Content-Type: application/json
```

**For Direct Railway API:**
```http
Authorization: Bearer [jwt_token_from_login]
Content-Type: application/json
```

## 📱 iOS App Recommendations

### Core Endpoints for MVP:
1. **Authentication**: `/api/v1/auth/login`, `/api/v1/auth/register`
2. **Product Search**: `/api/v1/products/nlp-search`
3. **Product Details**: `/api/v1/products/{code}`
4. **Health Assessment**: `/api/v1/products/{code}/health-assessment-mcp`

### Nice-to-Have for Later:
1. **User Profile**: `/api/v1/users/me`
2. **Favorites**: `/api/v1/users/favorites`
3. **History**: `/api/v1/users/history`
4. **Recommendations**: `/api/v1/users/explore`

## 🎯 Status Legend
- ✅ **Working**: Fully functional, ready for production use
- ⚠️ **Issues**: May have implementation issues, test before use
- 🔒 **Auth Required**: Requires user authentication
- ❌ **Public**: No authentication needed

## 📊 Summary
- **Total Endpoints**: 19
- **Working Public**: 7
- **Auth Required**: 9
- **Health/Status**: 3

Perfect for iOS development with a clean, simple API structure!