# Railway Deployment Guide

## 🚀 Quick Deployment

### **Method 1: Automatic Deployment (Preferred)**
When Railway auto-deploy is working correctly:
1. Make changes to your code
2. Commit and push to the connected branch
3. Railway automatically detects and deploys

```bash
git add .
git commit -m "Your changes"
git push origin migration-to-personal
```

### **Method 2: Manual CLI Deployment**
When auto-deploy isn't working or you need to force a deployment:

```bash
# Check Railway CLI is installed and logged in
railway --version
railway whoami

# Check current project status
railway status

# Deploy manually
railway up
```

### **Method 3: Manual Dashboard Deployment**
1. Go to Railway Dashboard → Your Project
2. Click **"Deploy"** button
3. Select the desired commit
4. Click **"Deploy Now"**

---

## 🔧 Troubleshooting Deployment Issues

### **Issue: Railway Not Detecting New Commits**

**Symptoms:**
- New commits pushed to GitHub
- Railway dashboard shows no recent deployments
- Auto-deploy seems broken

**Solutions:**

1. **Check Railway-GitHub Connection:**
   - Railway Dashboard → Settings → Source
   - Verify repository and branch are correct
   - Ensure "Auto Deploy" is enabled

2. **Reconnect Repository:**
   - Disconnect current repository
   - Reconnect to GitHub repository
   - Select correct branch (`migration-to-personal`)

3. **Use Railway CLI (Fastest Fix):**
   ```bash
   railway login  # If not logged in
   railway up     # Force deploy current code
   ```

4. **Check GitHub Webhooks:**
   - GitHub → Repository → Settings → Webhooks
   - Look for Railway webhook
   - Check recent delivery status

### **Issue: Build Failures**

**Common Causes:**
- Missing environment variables
- Python dependency conflicts
- Port configuration issues

**Solutions:**
1. Check Railway logs for specific error messages
2. Verify environment variables are set correctly
3. Ensure `requirements.txt` is up to date
4. Check `Procfile` and `start.sh` configuration

### **Issue: Service Won't Start**

**Check These Files:**
- `Procfile`: Should contain `web: ./start.sh`
- `start.sh`: Should be executable and contain correct startup command
- Environment variables: Especially `PORT`, `DATABASE_URL`, `SUPABASE_URL`

---

## 📁 Railway Configuration Files

### **Required Files:**

**`Procfile`**
```
web: ./start.sh
```

**`start.sh`**
```bash
#!/bin/bash
echo "🚀 Starting Clear-Meat API on Railway with Performance Optimizations..."
echo "PORT: $PORT"
echo "ENVIRONMENT: $ENVIRONMENT"  
echo "Python version: $(python --version)"

# Start the application
python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info
```

**`requirements.txt`**
- Must contain all Python dependencies
- Keep updated with project requirements

---

## 🔐 Environment Variables

### **Required in Railway:**
```bash
# Database
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# Security
SECRET_KEY=your-secure-key

# AI Services
GEMINI_API_KEY=AIza...

# Environment
ENVIRONMENT=production
DEBUG=false
```

### **Setting Environment Variables:**
1. Railway Dashboard → Your Project → Variables
2. Add each variable with key-value pairs
3. Redeploy if needed

---

## 📊 Performance Optimization Deployment

### **Recent Performance Updates (Latest Deployment):**

**What Was Deployed:**
- ✅ 96% faster recommendations endpoint (6 seconds → 0.2 seconds)
- ✅ Smart caching system with 5-minute TTL
- ✅ Optimized SQL queries (1000 → 150 products max)
- ✅ Fallback strategy for reliability

**Files Modified:**
- `app/services/recommendation_service.py` - Core performance optimizations
- `start.sh` - Updated startup message

**Performance Results:**
- **Before**: 5,000-7,000ms response time
- **After**: 200-600ms average response time
- **Cache hits**: ~15ms response time
- **Improvement**: 90%+ faster for Scanivore explore page

---

## 🚨 Emergency Deployment Commands

### **Quick Fix Deployment:**
```bash
# Force deployment with empty commit
git commit --allow-empty -m "Force Railway deployment"
git push origin migration-to-personal

# Or use CLI
railway up
```

### **Rollback to Previous Version:**
1. Railway Dashboard → Deployments
2. Find working deployment
3. Click "Redeploy" on that version

### **Check Deployment Status:**
```bash
railway status
railway logs  # View recent logs
```

---

## 📝 Best Practices

1. **Always test locally first** before deploying
2. **Use meaningful commit messages** for easier tracking
3. **Monitor Railway logs** during deployment
4. **Set up environment variables** before first deployment
5. **Keep Railway CLI updated** for latest features
6. **Use Railway CLI for urgent deployments** when dashboard is slow

---

## 🔗 Useful Railway Commands

```bash
# Basic commands
railway login
railway logout
railway status
railway logs
railway up

# Project management
railway projects
railway link [project-id]
railway environment

# Variables
railway variables
railway variables set KEY=value
railway variables delete KEY

# Services
railway services
railway connect [service-name]
```

---

## 📞 Support

- **Railway Documentation**: https://docs.railway.app
- **Railway Discord**: https://discord.gg/railway
- **GitHub Issues**: Check repository issues for deployment problems
- **CLI Help**: `railway help` or `railway [command] --help`