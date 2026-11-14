import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import Engine

from app.database import Base, engine
from app.routers.ai_insights import router as ai_insights_router
from app.routers.auth import build_auth_router, load_auth_settings, verify_session
from app.routers.dashboard import router as dashboard_router
from app.routers.exports import router as exports_router
from app.routers.savings_goals import router as savings_goals_router
from app.routers.transactions import router as transactions_router


def create_app(database_engine: Engine = engine) -> FastAPI:
    production = os.getenv("APP_ENV", "development").lower() == "production"
    database_url = os.getenv("DATABASE_URL", "")
    if production and not database_url.startswith(
        ("postgresql://", "postgresql+psycopg://")
    ):
        raise RuntimeError("DATABASE_URL must point to PostgreSQL in production")
    auth_settings = load_auth_settings()
    if production and auth_settings is None:
        raise RuntimeError("APP_USERNAME, APP_PASSWORD_HASH and APP_SECRET_KEY are required")

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        Base.metadata.create_all(bind=database_engine)
        yield

    application = FastAPI(
        title="Income & Expense Tracker",
        description="Personal income, expense, and savings goal tracker.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )
    application.include_router(
        transactions_router, prefix="/api/transactions", tags=["transactions"]
    )
    application.include_router(ai_insights_router, prefix="/api/ai", tags=["ai-insights"])
    application.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
    application.include_router(exports_router, prefix="/api/exports", tags=["exports"])
    application.include_router(
        build_auth_router(auth_settings), prefix="/api/auth", tags=["auth"]
    )
    application.include_router(
        savings_goals_router, prefix="/api/savings-goals", tags=["savings-goals"]
    )

    @application.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        """Return a simple status response for local development."""
        return {"status": "ok"}

    @application.get("/api/hello", tags=["example"])
    def hello() -> dict[str, str]:
        """Example API endpoint used by the separate frontend."""
        return {"message": "เชื่อมต่อ FastAPI สำเร็จ"}

    @application.middleware("http")
    async def protect_api(request, call_next):
        if request.url.path.startswith("/api/"):
            if auth_settings is not None:
                if request.method not in {"GET", "HEAD", "OPTIONS"}:
                    origin = request.headers.get("origin")
                    host = request.headers.get("host")
                    parsed_origin = urlsplit(origin or "")
                    if (
                        parsed_origin.scheme not in {"http", "https"}
                        or not host
                        or parsed_origin.netloc.lower() != host.lower()
                        or parsed_origin.path
                        or parsed_origin.query
                        or parsed_origin.fragment
                    ):
                        return JSONResponse(status_code=403, content={"detail": "Invalid origin"})

                public_auth_paths = {
                    "/api/auth/status",
                    "/api/auth/login",
                    "/api/auth/logout",
                }
                if request.url.path not in public_auth_paths:
                    session_cookie = request.cookies.get("money_session")
                    if not verify_session(session_cookie, auth_settings):
                        return JSONResponse(
                            status_code=401, content={"detail": "Authentication required"}
                        )

        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        if production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
                "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
            )
        return response

    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        application.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return application


app = create_app()
