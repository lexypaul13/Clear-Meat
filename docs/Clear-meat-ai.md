# Clear-Meat AI - Complete Project Documentation

## 🥩 Project Overview

Clear-Meat AI is a comprehensive health assessment platform for meat products, providing AI-powered nutritional analysis, ingredient risk evaluation, and personalized recommendations. Built with FastAPI and deployed on Railway, it serves as the backend for mobile applications focused on helping consumers make informed decisions about meat products.

### Key Features
- 🤖 AI-powered health assessments using Google Gemini
- 📱 Mobile-optimized API endpoints with 93% bandwidth reduction
- 🔍 Natural language product search
- 📊 Evidence-based ingredient analysis
- 🎯 Personalized product recommendations
- 🔐 Secure authentication with JWT tokens
- 📚 Complete Swagger API documentation

## 🏗️ System Architecture Overview

Clear-Meat AI uses a modern cloud-native architecture optimized for scalability and performance.

### Current Architecture (Production)

```
Mobile App/Client
       ↓
Supabase Edge Function (API Gateway)
       ↓
Railway (Python FastAPI)
       ↓
Supabase Database (PostgreSQL)
```

## 🚀 Deployment Infrastructure

### Production Environment
- **API Backend**: Railway (`https://clear-meat-api-production.up.railway.app`)
- **Database**: Supabase PostgreSQL
- **API Gateway**: Supabase Edge Functions
- **Authentication**: Supabase Auth (with bypass for development)

### Key URLs
- **Railway API**: `https://clear-meat-api-production.up.railway.app`
- **Supabase Project**: `https://ksgxendfsejkxhrmfsbi.supabase.co`
- **Edge Function**: `https://ksgxendfsejkxhrmfsbi.supabase.co/functions/v1/clear-meat-api`

## 🔧 Environment Configuration

### Railway Environment Variables
```bash
ENVIRONMENT=development                    # Allows auth bypass
ENABLE_AUTH_BYPASS=true                   # Disables auth middleware
DATABASE_URL=postgresql://...             # Supabase connection
SUPABASE_URL=https://...supabase.co      
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIs...     # Anon key
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1... # Service role key
GEMINI_API_KEY=AIzaSy...                 # Google Gemini API
SECRET_KEY=...                           # JWT secret
```

### Important Security Notes
- **Auth Bypass**: Currently enabled for development/testing
- **MCP Features**: Temporarily disabled (requires `fastmcp` package)
- **API Keys**: All sensitive keys stored as environment variables

## 📁 Project Structure

### Core Application (`/app`)
```
app/
├── main.py                 # FastAPI application entry point
├── core/                   # Core configuration and settings
├── api/                    # API route definitions
├── services/               # Business logic services
├── models/                 # Pydantic data models
├── middleware/             # Custom middleware (auth, caching, etc.)
├── db/                     # Database connections and sessions
└── utils/                  # Utility functions
```

### Key Services
- **Health Assessment**: AI-powered product analysis using Gemini
- **Product Search**: Advanced search with filtering
- **Recommendation Engine**: Personalized product suggestions
- **Authentication**: JWT-based auth with Supabase integration
- **Caching**: Redis-compatible caching layer

### Database Layer
- **Primary**: Supabase PostgreSQL with Row Level Security (RLS)
- **Caching**: In-memory cache with Redis fallback
- **Migrations**: Located in `/supabase/migrations`

## 🤖 AI Features

### Health Assessment Service
- **Engine**: Google Gemini Pro
- **Input**: Product ingredients and nutritional data
- **Output**: Risk rating, health insights, and recommendations
- **Status**: ✅ Active (MCP features disabled)

### MCP (Model Context Protocol) Integration
- **Status**: 🚧 Disabled (requires setup)
- **Purpose**: Evidence-based assessments with real scientific citations
- **Dependencies**: `fastmcp`, `pymed`, `crossref-commons`

## 🛠️ Development Setup

### Prerequisites
- Python 3.11 or higher
- PostgreSQL (via Supabase)
- Git
- Railway CLI (optional for deployment)

### Local Development - Quick Start

#### 1. Clone the Repository
```bash
git clone https://github.com/lexypaul13/Clear-Meat.git
cd Clear-Meat
```

#### 2. Create Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
# Upgrade pip
pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt
```

#### 4. Environment Configuration
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

Required environment variables:
```bash
# Core Settings
ENVIRONMENT=development
SECRET_KEY=your-secret-key-here

# Database (Supabase)
DATABASE_URL=postgresql://user:password@host:port/database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# AI Service
GEMINI_API_KEY=your-gemini-api-key

# Optional for development
ENABLE_AUTH_BYPASS=true
```

#### 5. Run the Application
```bash
# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the Python module approach
python -m uvicorn app.main:app --reload

# The API will be available at:
# http://localhost:8000
# Swagger docs at: http://localhost:8000/api/v1/docs
```

### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_security.py -v
python -m pytest tests/test_performance.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html

# Run a specific endpoint test
python -m pytest tests/test_api.py::test_health_endpoint -v
```

### Development Tools
```bash
# Format code with black
black app/

# Lint with flake8
flake8 app/

# Type checking with mypy
mypy app/

# Sort imports
isort app/
```

## 🚢 Deployment Guide

### Railway Deployment - Complete Guide

#### Prerequisites for Railway
1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Repository**: Fork or clone the project
3. **Railway CLI** (optional): `npm install -g @railway/cli`

#### Method 1: Deploy via Railway Dashboard (Recommended)

1. **Connect GitHub Repository**
   ```
   1. Go to https://railway.app/dashboard
   2. Click "New Project"
   3. Select "Deploy from GitHub repo"
   4. Choose your Clear-Meat repository
   5. Railway will auto-detect the Python app
   ```

2. **Configure Environment Variables**
   ```
   In Railway Dashboard > Variables:
   
   # Required Variables
   ENVIRONMENT=production
   SECRET_KEY=<generate-secure-key>
   DATABASE_URL=<supabase-postgresql-url>
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=<anon-key>
   SUPABASE_SERVICE_KEY=<service-key>
   GEMINI_API_KEY=<google-gemini-key>
   
   # Optional
   ENABLE_AUTH_BYPASS=false  # Set to true for testing
   PORT=8000
   ```

3. **Deploy**
   - Railway automatically deploys on push to main branch
   - Monitor deployment in the Railway dashboard
   - View logs: Dashboard > Deployments > View Logs

#### Method 2: Deploy via Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project in your Clear-Meat directory
cd Clear-Meat
railway link

# Deploy the application
railway up

# Set environment variables
railway variables set ENVIRONMENT=production
railway variables set DATABASE_URL=postgresql://...
railway variables set SUPABASE_URL=https://...
# ... set all required variables

# View deployment URL
railway open
```

#### Railway Configuration Files

**`railway.json`** - Railway configuration:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "numReplicas": 1,
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**`Procfile`** - Process definition:
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**`runtime.txt`** - Python version:
```
python-3.11.7
```

#### Monitoring & Maintenance

**View Logs**:
```bash
# Via CLI
railway logs

# Via Dashboard
# Go to project > Deployments > View Logs
```

**Check Deployment Status**:
```bash
# Health check
curl https://your-app.railway.app/health

# API status
curl https://your-app.railway.app/api/v1/docs
```

**Update Deployment**:
```bash
# Push to GitHub (auto-deploys)
git add .
git commit -m "Update feature"
git push origin main

# Or manual deploy
railway up
```

### Supabase Setup

#### 1. Create Supabase Project
```
1. Go to https://supabase.com/dashboard
2. Click "New Project"
3. Configure:
   - Name: clear-meat-db
   - Database Password: <secure-password>
   - Region: Choose closest to users
```

#### 2. Database Setup
```sql
-- Run migrations from /supabase/migrations/
-- These create all required tables and RLS policies
```

#### 3. Get Connection Details
```
Dashboard > Settings > API:
- URL: https://xxxxx.supabase.co
- Anon Key: eyJhbGc...
- Service Key: eyJhbGc... (keep secret!)

Dashboard > Settings > Database:
- Connection String: postgresql://...
```

### Supabase Edge Function (Optional API Gateway)
Located in `/supabase/functions/clear-meat-api/`

**Deploy Edge Function**:
```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Deploy function
supabase functions deploy clear-meat-api

# Set secrets
supabase secrets set RAILWAY_API_URL=https://your-app.railway.app
```

**Benefits**:
- Acts as API gateway
- Handles CORS automatically
- Provides additional auth layer
- Can transform requests/responses

## 📊 API Documentation

### Swagger/OpenAPI Documentation
**Access the interactive API documentation:**
- **Local**: `http://localhost:8000/api/v1/docs`
- **Production**: `https://clear-meat-api-production.up.railway.app/api/v1/docs`

### Key API Endpoints

#### 🏥 Health & Status
```bash
# Application health check
GET /health
Response: {"status": "healthy", "timestamp": 1234567890}

# Database connectivity
GET /health/db
Response: {"status": "healthy", "database": "connected"}

# Supabase integration
GET /health/supabase
Response: {"status": "healthy", "supabase": "connected"}
```

#### 🥩 Products
```bash
# List all products (paginated)
GET /api/v1/products/?skip=0&limit=20&risk_rating=Green
Headers: Authorization: Bearer <token>

# Natural language search
GET /api/v1/products/nlp-search?q=low sodium chicken&limit=10

# Get specific product
GET /api/v1/products/{barcode}

# Get product alternatives
GET /api/v1/products/{barcode}/alternatives

# AI Health Assessment (NEW - Mobile Optimized!)
GET /api/v1/products/{barcode}/health-assessment-mcp
GET /api/v1/products/{barcode}/health-assessment-mcp?format=mobile
Headers: Authorization: Bearer <token>
```

#### 🔐 Authentication
```bash
# Login (OAuth2 compatible)
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded
Body: username=email@example.com&password=yourpassword

# Register new user
POST /api/v1/auth/register
Content-Type: application/json
Body: {
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}

# OAuth providers
GET /api/v1/auth/providers
GET /api/v1/auth/oauth/{provider}

# Phone authentication
POST /api/v1/auth/phone/send-otp
POST /api/v1/auth/phone/verify
```

#### 👤 User Management
```bash
# Get current user profile
GET /api/v1/users/me
Headers: Authorization: Bearer <token>

# Update profile
PUT /api/v1/users/me
Headers: Authorization: Bearer <token>

# User favorites
GET /api/v1/users/favorites
POST /api/v1/users/favorites
DELETE /api/v1/users/favorites/{product_code}

# Scan history
GET /api/v1/users/history
POST /api/v1/users/history

# Personalized recommendations
GET /api/v1/users/recommendations
GET /api/v1/users/explore
```

### Mobile App Integration Example

#### iOS Swift Example
```swift
// Health Assessment - Mobile Optimized
func getHealthAssessment(barcode: String) async throws -> HealthAssessment {
    let url = URL(string: "\(baseURL)/api/v1/products/\(barcode)/health-assessment-mcp?format=mobile")!
    
    var request = URLRequest(url: url)
    request.setValue("Bearer \(authToken)", forHTTPHeaderField: "Authorization")
    request.setValue("gzip", forHTTPHeaderField: "Accept-Encoding")
    
    let (data, response) = try await URLSession.shared.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse,
          httpResponse.statusCode == 200 else {
        throw APIError.invalidResponse
    }
    
    return try JSONDecoder().decode(HealthAssessment.self, from: data)
}
```

#### Response Format (Mobile Optimized)
```json
{
  "summary": "This product contains preservatives requiring moderation...",
  "grade": "C",
  "color": "Yellow",
  "high_risk": [
    {
      "name": "Sodium nitrite",
      "risk": "Linked to potential carcinogenic effects..."
    }
  ],
  "moderate_risk": [...],
  "nutrition": [
    {
      "nutrient": "Salt",
      "amount": "2350 mg",
      "eval": "high",
      "comment": "High sodium content..."
    }
  ],
  "meta": {
    "product": "Product Name",
    "generated": "2025-06-26"
  }
}
```

## 🔒 Security Features

### Authentication & Authorization
- JWT-based authentication
- Supabase Auth integration
- Row Level Security (RLS) on database
- Rate limiting middleware

### Data Protection
- Input validation with Pydantic
- SQL injection protection via SQLAlchemy
- CORS configuration
- Secure headers middleware

## 📈 Performance Optimizations

### Caching Strategy
- **Application**: In-memory cache with TTL
- **Database**: Query result caching
- **API**: Response caching for static data

### Database Optimizations
- Indexed columns for search performance
- Text similarity search for ingredients
- Optimized queries for product filtering

## 🐛 Troubleshooting Common Issues

### Railway Deployment Issues

**Problem: Build fails on Railway**
```bash
# Solution 1: Check Python version
# Ensure runtime.txt has: python-3.11.7

# Solution 2: Check requirements.txt
# Remove any packages with @ git+ references
# Use only PyPI packages

# Solution 3: Clear cache and redeploy
railway up --no-cache
```

**Problem: App crashes after deployment**
```bash
# Check logs for missing env variables
railway logs

# Common missing variables:
- DATABASE_URL (must be PostgreSQL format)
- SUPABASE_URL (must include https://)
- PORT (Railway provides this automatically)
```

**Problem: Cannot connect to database**
```bash
# Verify DATABASE_URL format:
postgresql://user:password@host:port/database

# Test connection locally:
psql $DATABASE_URL

# Check Supabase dashboard for connection pooling settings
```

### Local Development Issues

**Problem: Module import errors**
```bash
# Solution: Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}"

# Or run with module syntax:
python -m uvicorn app.main:app --reload
```

**Problem: Supabase auth errors**
```bash
# For local development, set:
ENABLE_AUTH_BYPASS=true

# Check JWT token format:
# Must be: Bearer eyJhbGc...
```

**Problem: Gemini API errors**
```bash
# Verify API key is valid:
curl -X POST https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=YOUR_KEY

# Check quota limits in Google Cloud Console
```

### Performance Optimization

**Slow API responses**
```python
# Enable response caching
# Already implemented for health assessments (24hr TTL)

# Use mobile format for 93% size reduction:
GET /api/v1/products/{code}/health-assessment-mcp?format=mobile

# Enable gzip compression (already configured)
```

**Database query optimization**
```sql
-- Check slow queries
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Add indexes for common searches
CREATE INDEX idx_products_name_gin ON products USING gin(name gin_trgm_ops);
```

## 📈 Performance & Scaling

### Current Performance Metrics
- **API Response Time**: <200ms average
- **Health Assessment**: ~1-2s (with AI processing)
- **Mobile Optimized**: 93% bandwidth reduction
- **Concurrent Users**: Supports 100+ simultaneous

### Scaling Strategies

#### Horizontal Scaling (Railway)
```json
// railway.json
{
  "deploy": {
    "numReplicas": 3,  // Increase replicas
    "restartPolicyType": "ON_FAILURE"
  }
}
```

#### Database Optimization
- Connection pooling via Supabase
- Read replicas for heavy queries
- Materialized views for analytics

#### Caching Strategy
- In-memory cache: 5-minute TTL for products
- API response cache: 24-hour for assessments
- CDN for static assets

## 🔄 CI/CD Pipeline

### GitHub Actions (Recommended Setup)
```yaml
# .github/workflows/deploy.yml
name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Railway
        run: npm i -g @railway/cli
        
      - name: Deploy
        run: railway up
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

### Pre-deployment Checks
```bash
# Run before deploying
python -m pytest tests/
python -m black app/ --check
python -m flake8 app/
python -m mypy app/
```

## 🎯 Best Practices

### API Development
1. **Always use Pydantic models** for request/response validation
2. **Implement proper error handling** with meaningful messages
3. **Use dependency injection** for database sessions
4. **Add comprehensive logging** for debugging
5. **Write tests** for new endpoints

### Security
1. **Never commit secrets** - use environment variables
2. **Validate all inputs** to prevent injection attacks
3. **Use HTTPS only** in production
4. **Implement rate limiting** for public endpoints
5. **Keep dependencies updated** regularly

### Performance
1. **Cache expensive operations** (AI assessments, complex queries)
2. **Use database indexes** for frequently searched fields
3. **Implement pagination** for list endpoints
4. **Optimize images** before storing
5. **Use async operations** where possible

## 📚 Project Structure Deep Dive

### Complete File Structure
```
Clear-Meat/
├── app/                           # Main application code
│   ├── main.py                   # FastAPI app entry point
│   ├── api/                      # API layer
│   │   └── v1/
│   │       ├── endpoints/        # Route handlers
│   │       │   ├── auth.py      # Authentication endpoints
│   │       │   ├── products.py  # Product endpoints (with MCP)
│   │       │   └── users.py     # User management
│   │       └── models.py        # Pydantic models
│   ├── core/                     # Core functionality
│   │   ├── config.py            # Settings management
│   │   ├── security.py          # JWT & auth logic
│   │   ├── cache.py             # Caching implementation
│   │   └── supabase.py          # Supabase client
│   ├── services/                 # Business logic
│   │   ├── health_assessment_mcp_service.py  # AI health analysis
│   │   ├── recommendation_service.py         # Product recommendations
│   │   └── search_service.py                 # Search functionality
│   ├── middleware/               # Custom middleware
│   │   ├── auth.py              # Authentication middleware
│   │   ├── security.py          # Security headers
│   │   └── caching.py           # Response caching
│   ├── models/                   # Data models
│   │   ├── product.py           # Product schemas
│   │   └── user.py              # User schemas
│   └── utils/                    # Utilities
│       └── helpers.py           # Helper functions
├── tests/                        # Test suite
│   ├── test_api.py              # API endpoint tests
│   ├── test_security.py         # Security tests
│   └── test_performance.py      # Performance tests
├── docs/                         # Documentation
│   ├── Clear-meat-ai.md         # This file!
│   └── AVAILABLE_ENDPOINTS.md   # Endpoint reference
├── supabase/                     # Supabase configuration
│   ├── migrations/              # Database migrations
│   └── functions/               # Edge functions
├── scripts/                      # Utility scripts
├── requirements.txt             # Python dependencies
├── railway.json                 # Railway config
├── Procfile                     # Process definition
├── runtime.txt                  # Python version
└── .env.example                 # Environment template
```

## 🔗 Quick Links & Resources

### Official Documentation
- **FastAPI Docs**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **Railway Docs**: [docs.railway.app](https://docs.railway.app)
- **Supabase Docs**: [supabase.com/docs](https://supabase.com/docs)
- **Google Gemini**: [ai.google.dev](https://ai.google.dev)

### Project Resources
- **GitHub Repository**: [github.com/lexypaul13/Clear-Meat](https://github.com/lexypaul13/Clear-Meat)
- **Production API**: [clear-meat-api-production.up.railway.app](https://clear-meat-api-production.up.railway.app)
- **API Documentation**: [clear-meat-api-production.up.railway.app/api/v1/docs](https://clear-meat-api-production.up.railway.app/api/v1/docs)

### Development Tools
- **Postman Collection**: Export from Swagger UI
- **Database Schema**: See `/supabase/migrations/`
- **API Client Libraries**: Generate from OpenAPI spec

## 🚀 Getting Started Checklist

### For New Developers
- [ ] Clone repository
- [ ] Set up Python virtual environment
- [ ] Install dependencies
- [ ] Copy `.env.example` to `.env`
- [ ] Get API keys (Supabase, Gemini)
- [ ] Run local server
- [ ] Access Swagger docs
- [ ] Test an endpoint

### For Deployment
- [ ] Create Railway account
- [ ] Connect GitHub repository
- [ ] Set environment variables
- [ ] Deploy application
- [ ] Test production endpoints
- [ ] Monitor logs
- [ ] Set up alerts

### For Mobile Integration
- [ ] Review API documentation
- [ ] Test authentication flow
- [ ] Implement mobile-optimized endpoints
- [ ] Handle offline scenarios
- [ ] Implement caching
- [ ] Test on real devices

## 📞 Support & Contact

### Technical Support
1. **Check Documentation**: Review this guide and `/docs` folder
2. **View Logs**: Use Railway dashboard or CLI
3. **Debug Locally**: Run with `--reload` flag
4. **Check Issues**: GitHub repository issues

### Community
- **GitHub Discussions**: For questions and ideas
- **Issue Tracker**: For bug reports
- **Pull Requests**: Contributions welcome!

---

**Version**: 2.0  
**Last Updated**: June 2025  
**Maintainer**: Clear-Meat AI Team  
**License**: See LICENSE file  