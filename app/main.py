from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine

from app.database import Base, engine
from app.routers.ai_insights import router as ai_insights_router
from app.routers.dashboard import router as dashboard_router
from app.routers.savings_goals import router as savings_goals_router
from app.routers.transactions import router as transactions_router


def create_app(database_engine: Engine = engine) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        Base.metadata.create_all(bind=database_engine)
        yield

    application = FastAPI(
        title="Income & Expense Tracker",
        description="Personal income, expense, and savings goal tracker.",
        version="0.1.0",
        lifespan=lifespan,
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

    return application


app = create_app()
