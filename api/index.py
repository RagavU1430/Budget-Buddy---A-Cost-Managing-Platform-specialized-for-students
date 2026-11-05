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
        from app.db.session import engine, SessionLocal
        from app.services.storage import ensure_local_media_root
        from app.scripts.seed_demo_users import auto_seed_if_empty

        try:
            ensure_local_media_root()
        except Exception:
            pass

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with SessionLocal() as seed_session:
            await auto_seed_if_empty(seed_session)
    except Exception as exc:
        print("Database auto-init error:", exc)


class VercelPathFixMiddleware:
    """ASGI middleware to restore the original path and query string when Vercel rewrites to /api/index.py."""

    def __init__(self, asgi_app: ASGIApp):
        self.asgi_app = asgi_app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] in ("http", "websocket"):
            await ensure_db_initialized()

            query_bytes = scope.get("query_string", b"")
            query_str = query_bytes.decode("latin1", errors="ignore")
            query_params = parse_qs(query_str, keep_blank_values=True)

            if "__vercel_path__" in query_params:
                matched_subpath = query_params.pop("__vercel_path__")[0]
                clean_subpath = matched_subpath.lstrip("/")
                # The FastAPI app normalizes paths by adding /api prefix,
                # so we pass the path without /api here. The middleware will add it.
                new_path = f"/{clean_subpath}" if clean_subpath else "/api"
                scope["path"] = new_path
                scope["raw_path"] = new_path.encode("latin1")

                clean_pairs = []
                for k, vals in query_params.items():
                    for v in vals:
                        clean_pairs.append((k, v))
                new_query = urlencode(clean_pairs)
                scope["query_string"] = new_query.encode("latin1")
            elif scope.get("path") in ("/api", "/api/", "/api/index.py"):
                scope["path"] = "/api/health/"
                scope["raw_path"] = b"/api/health/"

        await self.asgi_app(scope, receive, send)


app.add_middleware(VercelPathFixMiddleware)
