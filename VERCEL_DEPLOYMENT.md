# BudgetBuddy Vercel Deployment Guide

## 🎯 Deployment Workflow

**Architecture:**
```
Vercel (Frontend) ↔ FastAPI Backend (on Render) ↔ Supabase (PostgreSQL)
```

This is a **hybrid deployment** where:
- **Vercel**: Serves the React frontend (budgetbuddy.vercel.app)
- **Render**: Hosts the FastAPI backend API
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

4. **Set project name:** `budgetbuddy`

### Step 2: Set Environment Variables in Vercel

**In Vercel Dashboard → Your Project → Settings → Environment Variables:**

| Variable | Value | Environment |
|----------|-------|-------------|
| `VITE_API_URL` | `https://budgetbuddy-api.onrender.com` | Production |
| `VITE_APP_NAME` | `Budget Buddy` | Production |
| `VITE_APP_VERSION` | `2.0.0` | Production |

### Step 3: Deploy Frontend to Vercel

```bash
cd frontend
vercel --prod
```

**Expected URL:** `https://budgetbuddy.vercel.app`

### Step 4: Deploy FastAPI Backend to Render

1. **Go to render.com** and create a new Web Service
2. **Service Configuration:**
   - Name: `budgetbuddy-api`
   - Root Directory: `backend-fastapi/`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

3. **Environment Variables in Render:**
   - `DATABASE_URL`: Your Supabase connection string
   - `SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"`
   - `CORS_ORIGINS`: `https://budgetbuddy-student.vercel.app,https://frontend-iota-black-70.vercel.app,http://localhost:5173`
   - `DEBUG`: `false`
   - `STORAGE_BACKEND`: `supabase`

4. **Add PostgreSQL Database:**
   - Create a new PostgreSQL database on Render
   - Copy the connection string to `DATABASE_URL`

### Step 5: Supabase Database Setup

**In Supabase Dashboard:**

1. **Database:**
   - Use the connection string from Render's PostgreSQL
   - Or create a new project at supabase.com

2. **Storage (Optional):**
   - Enable Storage bucket for report files
   - Configure API keys for file uploads

---

## 🔧 Configuration Files

### `.vercel.json` (Root directory)
```json
{
  "version": 2,
  "builds": [
    {
      "src": "frontend/package.json",
      "use": "@vercel/static-build",
      "config": {
        "distDirectory": "dist"
      }
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/index.html"
    }
  ]
}
```

### `render.yaml` (Root directory)
Already configured with:
- Backend web service
- PostgreSQL database
- Environment variable handling

---

## ✓ Verification Checklist

After deployment, verify:

- [ ] Frontend loads at: `https://budgetbuddy.vercel.app`
- [ ] API health check: `https://budgetbuddy-api.onrender.com/api/health/`
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

# Deploy backend (Render)
# Via Vercel dashboard: Connect GitHub → Configure → Deploy

# View logs
vercel logs budgetbuddy.vercel.app
```

---

## 🎉 Expected Deployment Summary

**Frontend:** `https://budgetbuddy.vercel.app`  
**Backend API:** `https://budgetbuddy-api.onrender.com`  
**Health Check:** `https://budgetbuddy-api.onrender.com/api/health/`

**Demo Accounts:**
- Student: student@budgetbuddy.local
- Premium: premium@budgetbuddy.local  
- Admin: admin@budgetbuddy.local

---

## 🆘 Troubleshooting

**CORS Errors:**
- Check `CORS_ORIGINS` in Render backend settings
- Ensure it includes `https://budgetbuddy.vercel.app`

**Database Connection Issues:**
- Verify `DATABASE_URL` in Render environment variables
- Check Supabase database is running

**Build Failures:**
- Run `npm install` and `npm run build` locally to test
- Check Vercel build logs in dashboard