# BudgetBuddy 💰🎓

> A full-stack personal budget planning and expense management platform designed for students to manage pocket money, track daily expenses, set savings goals, monitor spending habits, and build financial discipline.

---

## 📌 Project Overview

**BudgetBuddy** is designed specifically around student financial realities — irregular pocket money, scholarships, part-time freelance earnings, and common expense categories like food, travel, academic supplies, and social outings. 

The platform provides an end-to-end financial management experience:
- **Income & Expense Tracking:** Log and categorize daily transactions with flexible payment methods (Cash, UPI, Card, Net Banking).
- **Budget Planning:** Set monthly limits and category allocations with overspending alerts.
- **Savings Goals:** Set targets (e.g. *New Laptop Fund*, *Emergency Savings*, *Semester Trip*) and monitor progress.
- **Analytics & Reporting:** Interactive dashboards and exportable financial summaries (PDF & Excel).
- **Role-Based Experience:** Differentiated capabilities tailored for regular students, power/premium subscribers, and platform administrators.

---

## 👥 The 3 Roles & Permissions

| Feature / Capability | Student (`student`) | Premium (`premium`) | Admin (`admin`) |
|---|:---:|:---:|:---:|
| **Pocket Money & Income Tracking** | ✅ | ✅ | ✅ |
| **Daily Expense Categorization (Food, Travel, Books, etc.)** | ✅ | ✅ | ✅ |
| **Monthly Budget Limits & Utilization** | ✅ | ✅ | ✅ |
| **Basic Savings Goals** | ✅ | ✅ | ✅ |
| **Multi-category Advanced Budgets** | ❌ | ✅ | ✅ |
| **Automated Budget Alerts & Savings Reminders** | ❌ | ✅ | ✅ |
| **Report Generation & Export (PDF / Excel)** | ❌ | ✅ | ✅ |
| **Advanced Spending Analytics & Monthly Trends** | Basic | Advanced | System-wide |
| **User & Role Management (Promote to Premium/Admin)** | ❌ | ❌ | ✅ |
| **Global Category & System Logs Administration** | ❌ | ❌ | ✅ |

### Role Breakdown
- **🎓 Student:** The default tier for student users. Enables tracking allowances, logging transactions, viewing categorized history, and setting monthly spending caps.
- **⭐ Premium:** Unlocks advanced financial planning tools, custom savings milestone notifications, overspending warning triggers, and detailed monthly reports in PDF and Excel formats.
- **🛡️ Admin:** Access to administrative endpoints, user role assignment (`student` ↔ `premium` ↔ `admin`), category customization, and platform-wide metrics.

---

## 🛠️ Technology Stack

### Backend
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (High-performance async ASGI Python framework)
- **Database & ORM:** [SQLAlchemy 2.0 (Async)](https://www.sqlalchemy.org/) + `aiosqlite` / `asyncpg`
- **Authentication:** JWT (PyJWT + Argon2 password hashing, access + refresh token rotation)
- **Security & Headers:** CORSMiddleware, `python-dotenv`
- **AI Financial Intelligence:** Google Gemini AI with security guardrails & interactive clarification flows
- **Report Generation:** ReportLab (PDF) & openpyxl (Excel)
- **Testing:** `pytest` + `pytest-asyncio` + `httpx`

### Frontend
- **Framework & Tooling:** [React 19](https://react.dev/) + [Vite](https://vite.dev/)
- **Routing:** [React Router v7](https://reactrouter.com/)
- **Styling:** [Tailwind CSS v4](https://tailwindcss.com/)
- **HTTP Client:** [Axios](https://axios-http.com/) (with request/response interceptors for automatic JWT refresh)
- **State Management:** React Context API (`AuthContext`)
- **Icons:** `lucide-react`

---

## 📂 Repository Structure

```text
budgetbuddy/
├── .gitignore                    # Python, Node, venv, SQLite, .env exclusions
├── README.md                     # Project documentation & architecture guide
├── backend-fastapi/
│   ├── .env                      # Local environment secrets (untracked)
│   ├── .env.example              # Template environment variables
│   ├── pytest.ini                # Pytest configuration
│   ├── requirements.txt          # Python FastAPI & async dependencies
│   ├── app/
│   │   ├── main.py               # FastAPI application factory & router registration
│   │   ├── api/                  # REST API endpoints (auth, expenses, budgets, goals, assistant, reports, analytics)
│   │   ├── core/                 # Config (pydantic-settings), JWT security, serializers, pagination
│   │   ├── db/                   # SQLAlchemy 2.0 Async declarative models & session engine
│   │   └── services/             # Gemini AI Assistant, notifications, PDF/Excel report generators
│   └── tests/                    # Automated pytest integration test suite
└── frontend/
    ├── .env                      # Vite environment variables (untracked)
    ├── .env.example              # Vite environment template
    ├── package.json              # Frontend dependencies and build scripts
    ├── vite.config.js            # Vite + Tailwind v4 + React configuration
    ├── index.html
    └── src/
        ├── App.jsx               # Route definitions & protected route wrappers
        ├── main.jsx              # Application bootstrap & provider wrapping
        ├── index.css             # Tailwind CSS v4 entry
        ├── api/
        │   └── client.js         # Axios instance with JWT interceptor & refresh loop
        ├── context/
        │   └── AuthContext.jsx   # Global auth state, login, register, logout
        ├── components/           # Reusable UI components (Navbar, Layout, ProtectedRoute, AI Assistant)
        └── pages/                # Login, Register, Dashboard, Budgets, Goals, Transactions, Profile, Analytics
```

---

## 🚀 Deployment

### Option 1: Render (Recommended - Full-Stack)

Deploy both frontend and backend with a single `render.yaml` configuration:

```bash
# 1. Connect GitHub repo to Render
# 2. Add environment secrets:
#    - SECRET_KEY (64-character random string)
#    - GEMINI_API_KEY (Google Gemini API key)
# 3. Click "Manual Deploy"
```

See `render.yaml` for complete configuration.

### Option 2: Vercel + Render (Frontend on Vercel, Backend on Render)

**Frontend (Vercel):**
```bash
cd frontend
vercel --prod
```

Configure environment variables in Vercel dashboard:
- `VITE_API_URL` - Point to your Render backend (e.g., https://budgetbuddy.onrender.com)

**Backend (Render):**
```bash
# In Render dashboard:
# 1. Create new Web Service
# 2. Set Root Directory: backend-fastapi
# 3. Build Command: pip install -r requirements.txt
# 4. Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Option 3: Vercel Serverless (Experimental - Not Recommended for Production)

For API routes on Vercel, create files in `api/` directory:
- Each `.py` file becomes a serverless function
- FastAPI apps require custom ASGI adapter (see `api/` folder)

---

## 🚀 Getting Started

### Prerequisites
- **Python:** 3.11+ (tested on Python 3.13 / 3.14)
- **Node.js:** v18+ (tested on Node v24)
- **Git:** 2.x+

---

### Backend Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend-fastapi
   ```

2. **Create and activate a virtual environment:**
   - **Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   - **Windows:**
     ```powershell
     Copy-Item .env.example .env
     ```
   - **macOS / Linux:**
     ```bash
     cp .env.example .env
     ```

5. **Initialize Database Tables:**
   The SQLite / PostgreSQL schema initializes automatically on first startup via SQLAlchemy declarative metadata.

6. **(Optional) Run automated tests:**
   ```bash
   pytest -v
   ```

7. **Start the FastAPI development server:**
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   Backend will be running at `http://127.0.0.1:8000/`. Interactive Swagger API docs are available at `http://127.0.0.1:8000/docs`.

---

### Frontend Setup

1. **Open a new terminal and navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Set up environment variables:**
   - **Windows:**
     ```powershell
     Copy-Item .env.example .env
     ```
   - **macOS / Linux:**
     ```bash
     cp .env.example .env
     ```

3. **Install dependencies:**
   ```bash
   npm install
   ```

4. **Start Vite development server:**
   ```bash
   npm run dev
   ```
   Frontend will be running at `http://localhost:5173/`.

---

### Demo Accounts for Testing

Pre-configured demo users across all 3 roles:

| Role | Email | Password | Monthly Income |
|---|---|---|---|
| **🎓 Student** | `student@budgetbuddy.local` | *(Configured via `.env` or CLI)* | ₹12,000 |
| **⭐ Premium** | `premium@budgetbuddy.local` | *(Configured via `.env` or CLI)* | ₹25,000 |
| **🛡️ Admin** | `admin@budgetbuddy.local` | *(Configured via `.env` or CLI)* | ₹50,000 |

To seed or refresh demo accounts in the database:
```bash
# Seeds demo accounts and generates a secure one-time password (or reads DEMO_USER_PASSWORD from .env):
python manage.py seed_demo_users

# Or specify a custom password directly:
python manage.py seed_demo_users --password "YourSecurePass!123"
```
*(The Login page at `http://localhost:5173/login` provides 1-click quick-fill buttons for each demo role's email address).*

---

## 📡 API Endpoints Reference (Milestone 1)

| Method | Endpoint | Description | Auth Required | Permissions |
|---|---|---|:---:|---|
| `POST` | `/api/auth/register/` | Register new student account & receive tokens | ❌ | Anyone |
| `POST` | `/api/auth/login/` | Authenticate with email/password & receive tokens | ❌ | Anyone |
| `POST` | `/api/auth/token/refresh/` | Rotate / refresh access token with refresh token | ❌ | Anyone with refresh token |
| `GET` | `/api/auth/me/` | Retrieve profile and preferences of current user | ✅ | `IsAuthenticated` |
| `PATCH` | `/api/auth/me/` | Update profile (monthly income, currency, preferences) | ✅ | `IsAuthenticated` |
| `POST` | `/api/auth/change-password/` | Change password with old password verification | ✅ | `IsAuthenticated` |
| `GET` | `/api/auth/admin-only/` | Probe endpoint to verify admin privilege gate | ✅ | `IsAdminUser` (403 for student/premium) |
| `GET` | `/api/auth/admin/users/` | List all users and profiles on the platform | ✅ | `IsAdminUser` |
| `PATCH` | `/api/auth/admin/users/<id>/role/` | Promote/demote a user (`student`/`premium`/`admin`) | ✅ | `IsAdminUser` |

---

## 🧪 Automated Testing

Run the full pytest suite from the `backend-fastapi/` directory:
```bash
pytest -v
```
Integration tests verify:
- User registration with default `student` role and automatic `Profile` creation
- Duplicate email & username prevention
- Password confirmation mismatch validation
- JWT login returning access & refresh tokens
- Invalid credential rejection (401)
- Protected `/api/auth/me/` access control (401 for anonymous)
- AI assistant natural language budget setup with real-time database persistence
- Multi-turn conversational categorization for income and expense logging

---

## 📮 Postman Collection

Import the included `BudgetBuddy_Milestone_1.postman_collection.json` into Postman:
1. Open Postman ➔ Click **Import**.
2. Select `BudgetBuddy_Milestone_1.postman_collection.json`.
3. Requests automatically extract and update the `{{accessToken}}` and `{{refreshToken}}` variables upon running **Register** or **Login**.

---

## ✅ Milestone 1 Verification Checklist

- [x] Monorepo organized with clean separation (`backend/` + `frontend/`)
- [x] Custom User model extending `AbstractUser` with `role` choices (`student`, `premium`, `admin`)
- [x] Email configured as `USERNAME_FIELD` (unique, case-insensitive)
- [x] Auto-created `Profile` model with `post_save` signal
- [x] Complete database schema implemented (Income, Expense, Budget, SavingsGoal, Notification, Report)
- [x] Django Admin registered with filters, list displays, and search fields
- [x] JWT Authentication with SimpleJWT (access 30m, refresh 7d, rotation enabled)
- [x] CORS headers configured for Vite frontend (`http://localhost:5173`)
- [x] Role-Based Access Control (RBAC) permissions enforced on admin endpoints
- [x] React 19 + Vite frontend with Tailwind CSS v4 and Context API
- [x] Protected routes with automatic session restoration and token refresh on 401
- [x] 1-click Quick Fill demo accounts on Login page
- [x] 100% passing automated test suite (`pytest`)

---

## 🎬 Step-by-Step Demo Script

1. **Start the Backend:**
   ```powershell
   cd backend
   .\venv\Scripts\Activate.ps1
   python manage.py runserver 8000
   ```
2. **Start the Frontend:**
   ```powershell
   cd frontend
   npm run dev
   ```
3. **Open Browser:** Visit `http://localhost:5173`. You will be automatically redirected to `/login`.
4. **Test 1-Click Login:** Click the `🎓 Student` button and press **Sign in**. Notice instantaneous authentication into the Dashboard with monthly income displayed.
5. **Test Profile Editing:** Navigate to **Profile** in the navbar, update monthly income or currency, click **Save Profile**, and notice immediate updates.
6. **Test Logout & Role Switching:** Click **Sign out**, then click `⭐ Premium` or `🛡️ Admin` quick fill to test different role accounts.
7. **Verify Admin Security:** Open Postman or curl, authenticate as student, query `/api/auth/admin-only/` to see `403 Forbidden`. Authenticate as admin to see `200 OK`.
