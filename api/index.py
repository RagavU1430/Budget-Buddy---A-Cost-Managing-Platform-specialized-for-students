import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode
from starlette.types import ASGIApp, Receive, Scope, Send

# Add backend-fastapi directory to sys.path so app modules are discoverable
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend-fastapi"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.main import app

_db_initialized = False


async def ensure_db_initialized():
    global _db_initialized
    if _db_initialized:
        return
    _db_initialized = True
    try:
        from app.db.base import Base
        from app.db.session import engine
        from app.db.security_fix import apply_database_security_hardening

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with engine.connect() as conn:
            if conn.dialect.name == "postgresql":
                await apply_database_security_hardening(conn)
    except Exception as exc:
        print("Database auto-init error:", exc)


class VercelPathFixMiddleware:
    """ASGI middleware to handle Vercel serverless path rewrites.
    
    Vercel rewrites /api/* to /api/index.py?__vercel_path__=..., so the path reaching
    the app must be normalized back to the original FastAPI endpoint route.
    """

    def __init__(self, asgi_app: ASGIApp):
        self.asgi_app = asgi_app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] in ("http", "websocket"):
            await ensure_db_initialized()

            path = scope.get("path", "")
            query_bytes = scope.get("query_string", b"")
            query_str = query_bytes.decode("latin1", errors="ignore")
            query_params = parse_qs(query_str, keep_blank_values=True)

            if "__vercel_path__" in query_params:
                vercel_path = query_params.pop("__vercel_path__")[0].strip()
                scope["query_string"] = urlencode(query_params, doseq=True).encode("latin1")
                vercel_path = vercel_path.lstrip("/")
                new_path = f"/api/{vercel_path}" if vercel_path else "/api/health/"
                scope["path"] = new_path
                scope["raw_path"] = new_path.encode("latin1")
            elif path.startswith("/api/index.py"):
                # Strip /api/index.py prefix to get the actual API path
                new_path = path[len("/api/index.py"):] or "/"
                # Ensure it starts with /api for the FastAPI app's path normalization
                if not new_path.startswith("/api"):
                    new_path = f"/api{new_path}"
                scope["path"] = new_path
                scope["raw_path"] = new_path.encode("latin1")
            elif path in ("/api", "/api/"):
                scope["path"] = "/api/health/"
                scope["raw_path"] = b"/api/health/"

        await self.asgi_app(scope, receive, send)


app.add_middleware(VercelPathFixMiddleware)
