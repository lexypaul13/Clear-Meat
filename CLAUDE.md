# CLAUDE.md - Clear-Meat AI Project Guide

## 🚀 Quick Start Commands

### Development
```bash
# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
python -m pytest tests/ -v

# Code quality checks
black app/ && flake8 app/ && mypy app/
```

### Environment Setup
```bash
# Essential environment variables
export ENVIRONMENT=development
export ENABLE_AUTH_BYPASS=true  # For testing
export DATABASE_URL=postgresql://user:pass@host:port/db
export SUPABASE_URL=https://project.supabase.co
export GEMINI_API_KEY=your_key_here
```

## 🏗️ Architecture Overview

**Clear-Meat AI** is a FastAPI-based health assessment platform for meat products, deployed on Railway with Supabase PostgreSQL database.

### Core Stack
- **Backend**: FastAPI (Python 3.11)
- **Database**: Supabase PostgreSQL
- **AI Engine**: Google Gemini Pro
- **Deployment**: Railway
- **Authentication**: JWT + Supabase Auth

### Key Services
1. **Health Assessment Service** (`app/services/health_assessment_mcp_service.py`)
   - AI-powered product analysis using Google Gemini
   - FDA %DV nutrition calculations
   - Ingredient risk categorization
   - Mobile-optimized responses (93% size reduction)
   - **OPTIMIZED**: 94% performance improvement (5s vs 83s baseline)

2. **Recommendation Service** (`app/services/recommendation_service.py`)
   - Personalized product suggestions
   - Weighted scoring algorithm
   - Diversity factors for meat types

3. **Search Service** (`app/services/search_service.py`)
   - Natural language product search
   - PostgreSQL text similarity

## 📁 Project Structure

```
app/
├── main.py                 # FastAPI app + GZip middleware
├── api/v1/endpoints/       # Route handlers
│   ├── products.py         # Product endpoints + MCP health assessment
│   ├── auth.py             # Authentication (OAuth, JWT, Phone)
│   └── users.py            # User management + recommendations
├── services/               # Business logic
│   ├── health_assessment_mcp_service.py  # AI health analysis
│   └── recommendation_service.py         # Product recommendations
├── models/                 # Pydantic schemas
│   └── product.py          # HealthAssessment, Citation, NutritionInsight
└── core/                   # Configuration
    └── config.py           # Settings management
```

## 🎯 Critical Endpoints

### Health Assessment (Mobile Optimized)
```bash
GET /api/v1/products/{barcode}/health-assessment-mcp?format=mobile
```
- **Full response**: 3.5KB with complete analysis
- **Mobile response**: 1.2KB (65% smaller) 
- **Caching**: 24-hour TTL with versioned cache keys, 7-day ingredient cache
- **Compression**: GZip enabled (70-80% additional reduction)
- **Performance**: 5.07s average (94% improvement), instant cache hits

### Key Response Structure
```json
{
  "summary": "150-char summary...",
  "risk_summary": {"grade": "B", "color": "Yellow"},
  "ingredients_assessment": {
    "high_risk": [{"name": "...", "micro_report": "..."}],
    "moderate_risk": [...]
  },
  "nutrition_insights": [
    {"nutrient": "Salt", "amount_per_serving": "640 mg", "evaluation": "high"}
  ],
  "citations": [{"id": 1, "title": "...", "year": 2023}]
}
```

## 🔧 Development Patterns

### MCP Service Implementation
- Uses Google Gemini for health assessments
- FDA %DV calculations: ≥20% = high, 5-19% = moderate, <5% = low
- Cache handling with dict responses (NOT .model_dump())
- Mobile optimization function truncates responses

### Error Handling
- Always check if response is dict vs HealthAssessment object
- Handle both cached dict and fresh Pydantic model responses
- Use try/catch for nutrition value parsing

### Database Queries
- Use SQLAlchemy ORM for local DB
- Raw SQL for complex Supabase queries
- Pagination with skip/limit parameters

## 🚀 Deployment

### Railway Configuration
- Auto-deploy from GitHub main branch
- Environment: `ENVIRONMENT=production`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Required Environment Variables
```bash
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...supabase.co
SUPABASE_KEY=eyJhbGc...
SUPABASE_SERVICE_KEY=eyJhbGc...
GEMINI_API_KEY=AIzaSy...
SECRET_KEY=secure_random_key
```

## 📊 API Documentation

- **Swagger UI**: `/api/v1/docs`
- **Production**: https://clear-meat-api-production.up.railway.app/api/v1/docs
- All 19 endpoints have complete Swagger documentation

## 🔍 Common Issues & Solutions

### Cache Handling Bug
**Problem**: `AttributeError: 'dict' object has no attribute 'model_dump'`
**Solution**: Cache dict directly, don't call .model_dump() on dict objects

### Mobile Optimization
**Problem**: Large response sizes for mobile apps
**Solution**: Use `?format=mobile` parameter for 65% size reduction + GZip compression

### Authentication Bypass
**Problem**: Auth errors during development
**Solution**: Set `ENABLE_AUTH_BYPASS=true` in development environment

## 📚 Key Files to Know

- `app/services/health_assessment_mcp_service.py` - Core AI service
- `app/api/v1/endpoints/products.py` - Main product endpoints
- `app/models/product.py` - Response schemas
- `docs/Clear-meat-ai.md` - Complete project documentation

## 🎯 Best Practices

1. **Always test endpoints** with real product codes (e.g., `0002000003197`)
2. **Use mobile format** for app development (`?format=mobile`)
3. **Check Railway logs** for deployment issues
4. **Verify environment variables** before deployment
5. **Use Swagger UI** for API testing and integration

---
*This guide covers the essentials for working with Clear-Meat AI. For complete documentation, see `docs/Clear-meat-ai.md`.*