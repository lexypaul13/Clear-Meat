# Docker Setup for Clear-Meat API

This guide covers running the Clear-Meat API using Docker for development and production.

## 🐳 **Quick Start with Docker**

### **Option 1: Simple Docker Run (Recommended for Development)**

1. **Build the Docker image:**
   ```bash
   docker build -t clear-meat-api .
   ```

2. **Run with local Supabase (if you have Supabase running locally):**
   ```bash
   docker run -p 8000:8000 \
     -e ENABLE_AUTH_BYPASS=true \
     -e DATABASE_URL="postgresql://postgres:postgres@host.docker.internal:54322/postgres" \
     -e SECRET_KEY="super-secret-jwt-token-with-at-least-32-characters-long" \
     clear-meat-api
   ```

3. **Access the API:**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health

### **Option 2: Docker Compose (Full Stack)**

1. **Start the complete stack:**
   ```bash
   docker-compose up --build
   ```

2. **Access services:**
   - API: http://localhost:8000
   - Database: localhost:54322
   - Supabase API: http://localhost:54321

3. **Stop the stack:**
   ```bash
   docker-compose down
   ```

## 🔧 **Configuration**

### **Environment Variables**

The Docker setup includes these environment variables by default:

```bash
ENABLE_AUTH_BYPASS=true          # Skip authentication for development
DATABASE_URL=postgresql://...    # Database connection
SECRET_KEY=super-secret...       # JWT secret key
ENVIRONMENT=development          # Environment mode
DEBUG=true                       # Enable debug logging
```

### **Custom Configuration**

Create a `.env.docker` file for custom settings:

```bash
# .env.docker
ENABLE_AUTH_BYPASS=false
GEMINI_API_KEY=your-gemini-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
```

Then run with:
```bash
docker run --env-file .env.docker -p 8000:8000 clear-meat-api
```

## 🚀 **Production Docker Setup**

### **Production Dockerfile**

For production, create a `Dockerfile.prod`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY *.py ./

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### **Production Build**

```bash
# Build production image
docker build -f Dockerfile.prod -t clear-meat-api:prod .

# Run production container
docker run -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e DEBUG=false \
  -e ENABLE_AUTH_BYPASS=false \
  -e DATABASE_URL="your-production-db-url" \
  -e SUPABASE_URL="your-production-supabase-url" \
  -e SUPABASE_KEY="your-production-key" \
  -e SECRET_KEY="your-production-secret" \
  clear-meat-api:prod
```

## 🛠️ **Development Workflow**

### **Live Development with Docker**

For development with live reload:

```bash
# Mount source code for live editing
docker run -p 8000:8000 \
  -v $(pwd)/app:/app/app \
  -e ENABLE_AUTH_BYPASS=true \
  clear-meat-api
```

### **Database Management**

```bash
# Access database container
docker-compose exec supabase-db psql -U postgres -d postgres

# View logs
docker-compose logs api
docker-compose logs supabase-db

# Reset database
docker-compose down -v  # Removes volumes
docker-compose up --build
```

## 🔍 **Troubleshooting**

### **Common Issues**

1. **Port conflicts:**
   ```bash
   # Check what's using the port
   lsof -i :8000
   
   # Use different port
   docker run -p 8001:8000 clear-meat-api
   ```

2. **Database connection issues:**
   ```bash
   # Check if local Supabase is running
   curl http://localhost:54321/health
   
   # Use host.docker.internal for Mac/Windows
   # Use 172.17.0.1 for Linux
   ```

3. **Authentication bypass not working:**
   ```bash
   # Check environment variables
   docker run clear-meat-api env | grep ENABLE_AUTH_BYPASS
   
   # Test endpoint
   curl http://localhost:8000/api/v1/products/test/health-assessment
   ```

## 📝 **Notes**

- **Development**: Use `ENABLE_AUTH_BYPASS=true` for easy testing
- **Production**: Always set `ENABLE_AUTH_BYPASS=false` and use proper authentication
- **Database**: The Docker Compose setup includes a full Supabase stack
- **Volumes**: Database data persists in Docker volumes between restarts

## 🚨 **Security Warning**

**Never use `ENABLE_AUTH_BYPASS=true` in production!** This completely disables authentication and should only be used for local development and testing. 