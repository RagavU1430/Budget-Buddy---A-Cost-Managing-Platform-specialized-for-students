"""FastAPI Application factory and ASGI entrypoint for BudgetBuddy."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.analytics import router as analytics_router
from app.api.assistant import router as assistant_router
from app.api.auth import router as auth_router
from app.api.budgets import router as budgets_router
from app.api.expenses import router as expenses_router
from app.api.goals import router as goals_router
from app.api.notifications import router as notifications_router
from app.api.reports import router as reports_router
from app.core.config import settings
from app.core.errors import APIError
from app.db import models  # noqa: F401 - ensure all tables are registered on Base
from app.db.base import Base
from app.db.session import engine
from app.services.storage import ensure_local_media_root


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Ensure local media directory exists
    try:
        ensure_local_media_root()
    except Exception:
        pass

    # Automatically initialize tables in SQLite if needed
    if "sqlite" in settings.DATABASE_URL:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        try:
            from app.db.session import SessionLocal
            from app.scripts.seed_demo_users import auto_seed_if_empty
            async with SessionLocal() as seed_session:
                await auto_seed_if_empty(seed_session)
        except Exception:
            pass

    yield

    await engine.dispose()


app = FastAPI(
    title="BudgetBuddy API",
    description="FastAPI Backend for BudgetBuddy — Student Neo-Fintech & AI Budget Assistant",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX if settings.CORS_ORIGIN_REGEX else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for DRF parity error payloads
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(status_code=exc.status_code, content=exc.body)


# Normalize serverless paths (if deployment platform strips /api prefix)
@app.middleware("http")
async def normalize_api_path(request: Request, call_next):
    path = request.scope.get("path", "")
    if path and not path.startswith("/api") and path != "/" and not path.startswith("/docs") and not path.startswith("/redoc") and not path.startswith("/openapi"):
        request.scope["path"] = f"/api{path}"
    response = await call_next(request)
    return response


# Health check endpoint matching Django: /api/health/
@app.get("/api/health/")
@app.get("/api/health")
@app.get("/health/")
@app.get("/health")
@app.get("/")
async def health():
    return {"status": "ok", "service": "budgetbuddy-api"}


# Include API routers under /api and /api/auth
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(expenses_router, prefix="/api", tags=["expenses"])
app.include_router(budgets_router, prefix="/api", tags=["budgets"])
app.include_router(analytics_router, prefix="/api", tags=["analytics"])
app.include_router(goals_router, prefix="/api", tags=["goals"])
app.include_router(notifications_router, prefix="/api", tags=["notifications"])
app.include_router(reports_router, prefix="/api", tags=["reports"])
app.include_router(assistant_router, prefix="/api", tags=["assistant"])

# Static files for media uploads/reports if local
media_path = Path(settings.LOCAL_STORAGE_DIR)
media_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_path)), name="media")
