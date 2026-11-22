# BudgetBuddy Vercel & Railway Deployment Guide

## 🎯 Deployment Workflow

**Architecture:**
```
Vercel (Frontend) ↔ FastAPI Backend (on Railway) ↔ Supabase (PostgreSQL)
```

This is a **hybrid deployment** where:
- **Vercel**: Serves the React frontend (`budgetbuddy-app.vercel.app` / `budgetbuddy-app-six.vercel.app`)
- **Railway**: Hosts the FastAPI backend API (`https://<railway-domain>.up.railway.app`)
- **Supabase**: Provides the PostgreSQL database

---

## 🚀 Step-by-Step Deployment

### Step 1: Prepare Vercel for Frontend

1. **Install Vercel CLI:**
```bash
npm install -g vercel
```

2. **Login to Vercel:**
```bash
vercel login
```

3. **Link your project:**
```bash
cd frontend
vercel link
```

4. **Set project name:** `budgetbuddy-app`

### Step 2: Set Environment Variables in Vercel

**In Vercel Dashboard → Your Project → Settings → Environment Variables:**

| Variable | Value | Environment |
|----------|-------|-------------|
| `VITE_API_URL` | `https://<railway-domain>.up.railway.app/api` | Production |
| `VITE_APP_NAME` | `Budget Buddy` | Production |
| `VITE_APP_VERSION` | `2.0.0` | Production |

### Step 3: Deploy Frontend to Vercel

```bash
cd frontend
vercel --prod
```

**Expected URL:** `https://budgetbuddy-app.vercel.app` (or `https://budgetbuddy-app-six.vercel.app`)

### Step 4: Deploy FastAPI Backend to Railway

1. **Go to railway.app** and create a new Project (or use Railway MCP / CLI)
2. **Service Configuration:**
   - Source: Connect GitHub Repository
   - Root Directory: `backend-fastapi`
   - Build Provider: Nixpacks (auto-detected via `railway.json`)
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (auto-detected via `railway.json` and `Procfile`)
   - Healthcheck Path: `/api/health/`

3. **Environment Variables in Railway:**
   - `DATABASE_URL`: Your Supabase connection string (`postgresql+asyncpg://postgres:password@...:5432/postgres`)
   - `SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"`
   - `CORS_ORIGINS`: `https://budgetbuddy-app.vercel.app,https://budgetbuddy-app-six.vercel.app,https://budgetbuddy.vercel.app,https://budgetbuddy-student.vercel.app,https://frontend-iota-black-70.vercel.app,http://localhost:5173,https://*.up.railway.app`
   - `DEBUG`: `false`
   - `STORAGE_BACKEND`: `supabase`
   - `SMTP_HOST`: e.g. `smtp.gmail.com`
   - `SMTP_PORT`: `587`
   - `SMTP_USERNAME`: your SMTP email
   - `SMTP_PASSWORD`: your SMTP app password
   - `SMTP_FROM_EMAIL`: your SMTP sender email
   - `SMTP_USE_TLS`: `true`

4. **Generate Public Domain in Railway:**
   - In Service Settings → Networking → Public Networking: click "Generate Domain"
   - You will get a domain like `https://budgetbuddy-backend-production.up.railway.app`

### Step 5: Supabase Database Setup

**In Supabase Dashboard:**

1. **Database:**
   - Connect using the transaction or session pooler string from Supabase Project Settings
2. **Storage (Optional):**
   - Enable Storage bucket `reports` for file uploads

---

## 🔧 Configuration Files

### `.vercel.json` (Root directory)
Configures static SPA routing for the React frontend on Vercel:
```json
{
  "version": 2,
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

### `backend-fastapi/railway.json`
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/api/health/",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### `backend-fastapi/Procfile`
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## ✓ Verification Checklist

After deployment, verify:

- [ ] Frontend loads at: `https://budgetbuddy-app.vercel.app` (or `https://budgetbuddy-app-six.vercel.app`)
- [ ] API health check: `https://<railway-domain>.up.railway.app/api/health/`
- [ ] Login works with demo accounts
- [ ] Expenses can be logged
- [ ] Budgets can be created
- [ ] Reports can be generated

---

## 📝 Deployment Commands

```bash
# Deploy frontend (Vercel)
cd frontend
vercel --prod

# Deploy backend (Railway)
# Connect GitHub repo in Railway dashboard or run:
# railway up
```

---

## 🎉 Expected Deployment Summary

**Frontend:** `https://budgetbuddy-app.vercel.app`  
**Backend API:** `https://<railway-domain>.up.railway.app/api`  
**Health Check:** `https://<railway-domain>.up.railway.app/api/health/`

**Demo Accounts:**
- Student: student@budgetbuddy.local
- Premium: premium@budgetbuddy.local  
- Admin: admin@budgetbuddy.local

---

## 🆘 Troubleshooting

**CORS Errors:**
- Check `CORS_ORIGINS` in Railway backend settings
- Ensure it includes `https://budgetbuddy-app.vercel.app` and `https://budgetbuddy-app-six.vercel.app`

**Database Connection Issues:**
- Verify `DATABASE_URL` in Railway environment variables
- Check Supabase database is active
