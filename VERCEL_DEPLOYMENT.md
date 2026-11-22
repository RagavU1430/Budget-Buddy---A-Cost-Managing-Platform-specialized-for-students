# BudgetBuddy Vercel Full-Stack Serverless Deployment Guide

## 🎯 Architecture: 100% Serverless

```
Browser Client ↔ Vercel Edge/Serverless (Vite React + FastAPI Serverless) ↔ Supabase (PostgreSQL)
```

BudgetBuddy is deployed entirely on **Vercel** with zero standing servers:
- **Frontend**: Vite React Single Page Application served from Vercel Edge (`/`)
- **Backend**: FastAPI Serverless Python Functions (`api/index.py`) hosted on Vercel (`/api/*`)
- **Database**: Supabase PostgreSQL with connection pooling & Row Level Security (RLS)

All client API calls use the relative path `/api` (same origin), completely avoiding cross-origin (CORS) roundtrips in production.

---

## 🚀 Step-by-Step Deployment

### Step 1: Vercel Project Setup

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
vercel link
```

### Step 2: Set Environment Variables in Vercel

**In Vercel Dashboard → Your Project → Settings → Environment Variables:**

| Variable | Recommended Value | Environments | Purpose |
|----------|-------------------|--------------|---------|
| `VITE_API_URL` | `/api` | Production, Preview, Development | Base URL for API requests |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:[PASS]@[HOST]:5432/postgres` | Production, Preview | Supabase connection string |
| `SECRET_KEY` | 64+ char random string | Production, Preview | JWT token secret |
| `DEBUG` | `false` | Production | Disables debug endpoints and docs |
| `STORAGE_BACKEND` | `supabase` | Production | Report/file storage backend |
| `SUPABASE_URL` | `https://[PROJECT].supabase.co` | Production | Supabase project URL |
| `SUPABASE_KEY` | `eyJ...` (anon key) | Production | Supabase anon key |
| `SUPABASE_SECRET_KEY` | `eyJ...` (service role key) | Production | Supabase service key |
| `SMTP_HOST` | e.g. `smtp.gmail.com` | Production | Email verification server |
| `SMTP_PORT` | `587` | Production | SMTP port |
| `SMTP_USE_TLS` | `true` | Production | Enable STARTTLS |
| `SMTP_USERNAME` | your email | Production | SMTP auth username |
| `SMTP_PASSWORD` | your app password | Production | SMTP auth password |
| `SMTP_FROM_EMAIL` | your email | Production | Sender email |

### Step 3: Deploy to Vercel

```bash
vercel --prod
```

---

## 🔧 Serverless Configuration Files

### `vercel.json` (Root directory)
Configures building the frontend and routing API calls to the serverless Python handler `api/index.py`:

```json
{
  "version": 2,
  "regions": ["sin1"],
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/dist",
  "rewrites": [
    {
      "source": "/api",
      "destination": "/api/index.py?__vercel_path__=health/"
    },
    {
      "source": "/api/",
      "destination": "/api/index.py?__vercel_path__=health/"
    },
    {
      "source": "/api/(.*)",
      "destination": "/api/index.py?__vercel_path__=$1"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

### `api/index.py` (Serverless ASGI Entrypoint)
Provides the ASGI adapter with `VercelPathFixMiddleware` to reconstruct routes from `__vercel_path__` and ensure database initialization on cold start.

---

## ✓ Verification Checklist

After deployment, verify:

- [ ] Frontend loads at your Vercel URL (e.g., `https://budgetbuddy-app.vercel.app`)
- [ ] Serverless health check returns `{"status":"ok",...}`:
  `curl -i https://budgetbuddy-app.vercel.app/api/health/`
- [ ] User login and registration flow works with Supabase PostgreSQL
- [ ] JWT authentication tokens work with httpOnly cookie refresh loop
- [ ] Expense tracking, budget calculation, and analytics graphs display data
- [ ] AI Financial Assistant answers user queries

---

## 🆘 Troubleshooting

**Health check returns 500 / Function Invocation Failed:**
- Verify `DATABASE_URL` is set in Vercel project environment variables.
- Verify the Supabase database is active and accepting connections.
- Ensure `SECRET_KEY` is configured.

**404 Not Found on API routes:**
- Ensure `vercel.json` has the correct `/api/(.*)` rewrite to `/api/index.py?__vercel_path__=$1`.
