# Clear-Meat AI - Project Documentation

## 🏗️ System Architecture Overview

Clear-Meat AI is a FastAPI-based application that provides AI-powered health assessments for meat products. The system uses a modern cloud-native architecture with multiple deployment options.

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

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your credentials

# Run the application
python -m uvicorn app.main:app --reload
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python tests/security_test.py
python tests/performance_test.py
```

## 🚢 Deployment Guide

### Railway Deployment
The application is configured for Railway with these files:
- `Procfile`: Process definitions
- `railway.json`: Railway-specific configuration
- `runtime.txt`: Python version specification
- `start.sh`: Startup script

### Supabase Edge Function
Located in `/supabase/functions/clear-meat-api/`
- Acts as API gateway
- Handles CORS and authentication
- Proxies requests to Railway API

## 📊 API Endpoints

### Health & Status
- `GET /health` - Application health check
- `GET /health/db` - Database connectivity check
- `GET /health/supabase` - Supabase integration check

### Products
- `GET /api/v1/products/` - List products with filtering
- `GET /api/v1/products/{code}` - Get specific product
- `POST /api/v1/products/{code}/health-assessment` - AI health analysis

### Authentication
- `POST /api/v1/auth/login` - User authentication
- `POST /api/v1/auth/register` - User registration
- `GET /api/v1/auth/me` - Current user profile

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

## 🐛 Known Issues & Limitations

### Current Limitations
1. **MCP Features**: Disabled due to `fastmcp` dependency issues
2. **Authentication**: Bypass enabled for development
3. **Edge Function Routing**: Minor path resolution issues

### Planned Improvements
1. Re-enable MCP with proper package installation
2. Implement production authentication flow
3. Add comprehensive API documentation
4. Enhanced error handling and logging

## 📚 Additional Documentation

- **API Reference**: `/docs/API_README.md`
- **Database Guide**: `/docs/DATABASE_ENVIRONMENT_GUIDE.md`
- **Docker Setup**: `/docs/DOCKER_SETUP.md`
- **Architecture Details**: `/docs/SYSTEMS_ARCHITECTURE.md`

## 🆘 Troubleshooting

### Common Issues

**Railway Deployment Fails**
- Check environment variables are set correctly
- Verify `requirements.txt` has all dependencies
- Check Railway logs for specific errors

**Database Connection Issues**
- Verify `DATABASE_URL` format: `postgresql://...`
- Check Supabase project status
- Ensure RLS policies allow access

**Authentication Errors**
- Verify `ENABLE_AUTH_BYPASS=true` for development
- Check JWT secret key configuration
- Validate Supabase keys

### Debug Commands
```bash
# Check Railway status
railway status

# View Railway logs
railway logs

# Test API endpoints
curl https://clear-meat-api-production.up.railway.app/health

# Check environment variables
railway variables
```

## 📞 Support

For technical issues or questions:
1. Check the troubleshooting section above
2. Review logs in Railway dashboard
3. Consult the additional documentation in `/docs`
4. Check git commit history for recent changes

---

**Last Updated**: June 2025  
**Architecture Version**: v2.0 (Railway + Supabase)  
**API Version**: v1  