from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine

from app.database import Base, engine
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
