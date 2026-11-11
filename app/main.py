from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Income & Expense Tracker",
    description="Personal income, expense, and savings goal tracker.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return a simple status response for local development."""
    return {"status": "ok"}


@app.get("/api/hello", tags=["example"])
def hello() -> dict[str, str]:
    """Example API endpoint used by the separate frontend."""
    return {"message": "เชื่อมต่อ FastAPI สำเร็จ"}
