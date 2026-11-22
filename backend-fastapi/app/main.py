"""FastAPI Application factory and ASGI entrypoint for BudgetBuddy."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
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

    # Initialize tables for local development SQLite or when AUTO_MIGRATE is enabled.
    # In production serverless PostgreSQL, skip schema introspection to ensure instantaneous cold starts.
    if settings.DATABASE_URL.startswith("sqlite") or os.getenv("AUTO_MIGRATE", "").lower() in ("true", "1"):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception:
            pass

    # Validate production settings
    if not settings.DEBUG:
        db_url = os.getenv("DATABASE_URL", "")
        is_localhost = "localhost" in db_url or "127.0.0.1" in db_url
        if not is_localhost:
            # Verify SECRET_KEY is not default
            from app.core.config import DEFAULT_SECRET_KEY
            if settings.SECRET_KEY == DEFAULT_SECRET_KEY:
                import warnings
                warnings.warn(
                    "PRODUCTION WARNING: SECRET_KEY is using default value! "
                    "Generate a strong key with: python -c \"import secrets; print(secrets.token_urlsafe(64))\"",
                    RuntimeWarning,
                    stacklevel=2,
                )

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


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    # HSTS (only in production with HTTPS)
    if not settings.DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Permissions policy
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

# CORS Configuration - explicit origins and Railway deployment domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=getattr(settings, "CORS_ORIGIN_REGEX", r"^https://.*\.up\.railway\.app$"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin")
    if origin:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    return {}


# Exception handler for DRF parity error payloads
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(status_code=exc.status_code, content=exc.body, headers=_cors_headers(request))


# Exception handler for database data capacity / overflow errors
from sqlalchemy.exc import DBAPIError, DataError


@app.exception_handler(DataError)
async def data_error_handler(request: Request, exc: DataError):
    exc_str = str(exc).lower()
    if "numeric field overflow" in exc_str:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "The amount entered is too large and exceeds the maximum supported limit.",
                "amount": ["Ensure that there are no more than 14 digits before the decimal point."],
            },
            headers=_cors_headers(request),
        )
    return JSONResponse(
        status_code=400,
        content={"detail": "A provided value exceeds database field capacity.", "error": str(exc)},
        headers=_cors_headers(request),
    )


@app.exception_handler(DBAPIError)
async def dbapi_error_handler(request: Request, exc: DBAPIError):
    exc_str = str(exc).lower()
    if "numeric field overflow" in exc_str:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "The amount entered is too large and exceeds the maximum supported limit.",
                "amount": ["Ensure that there are no more than 14 digits before the decimal point."],
            },
            headers=_cors_headers(request),
        )
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred.", "error": str(exc)},
        headers=_cors_headers(request),
    )


# Catch-all exception handler to ensure CORS headers are preserved on unhandled errors
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    # Don't leak stack traces in production
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred.", "error": str(exc), "traceback": traceback.format_exc()},
            headers=_cors_headers(request),
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
        headers=_cors_headers(request),
    )


# Normalize serverless paths (if deployment platform strips /api prefix)
@app.middleware("http")
async def normalize_api_path(request: Request, call_next):
    path = request.scope.get("path", "")
    if (
        path
        and not path.startswith("/api")
        and path != "/"
        and not path.startswith("/docs")
        and not path.startswith("/redoc")
        and not path.startswith("/openapi")
        and not path.startswith("/assets")
        and not path.endswith(".html")
        and not path.endswith(".js")
        and not path.endswith(".css")
        and not path.endswith(".svg")
        and not path.endswith(".ico")
        and not path.endswith(".png")
        and not path.endswith(".json")
    ):
        request.scope["path"] = f"/api{path}"
    response = await call_next(request)
    return response


# Health check endpoint matching Django: /api/health/
@app.get("/api/health/")
@app.get("/api/health")
@app.get("/health/")
@app.get("/health")
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

# Static frontend SPA fallback (mount frontend/dist for Vercel serverless / full-stack deployment)
possible_dist_paths = [
    Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
    Path("frontend/dist"),
    Path("/var/task/frontend/dist"),
]
frontend_dist = next((p for p in possible_dist_paths if p.is_dir()), None)

if frontend_dist:
    index_html = frontend_dist / "index.html"

    @app.get("/index.html")
    @app.get("/")
    async def serve_index():
        if index_html.is_file():
            return FileResponse(index_html)
        return JSONResponse({"status": "ok", "service": "budgetbuddy-api"})

    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend-spa")
