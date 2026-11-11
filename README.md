# Income & Expense Tracker

Personal web app for tracking income, expenses, savings, and purchase goals. The frontend and backend run as separate development servers.

## Stack

- Frontend: Vite, HTML, CSS, and JavaScript (`http://127.0.0.1:5173`)
- Backend: FastAPI and Uvicorn (`http://127.0.0.1:8000`)
- Database: SQLite will be added in the database setup step

## Run locally

### 1. Start the backend

In the project root, create and activate a Python virtual environment, then install dependencies:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

FastAPI's interactive API docs are at <http://127.0.0.1:8000/docs>. Transaction endpoints are under `/api/transactions`:

- `POST /api/transactions` — create an income or expense
- `GET /api/transactions` — list transactions; optional filters: `type`, `start_date`, `end_date`
- `GET /api/transactions/{id}` — read one transaction
- `PUT /api/transactions/{id}` — replace a transaction
- `DELETE /api/transactions/{id}` — delete a transaction

Amounts use integer satang to keep calculations exact. Example request body:

```json
{
  "type": "expense",
  "amount_satangs": 12500,
  "date": "2026-11-11",
  "category": "อาหาร",
  "note": "มื้อกลางวัน"
}
```

The SQLite database is created at `data/app.db` the first time the backend starts. This file is ignored by Git.

## Run checks locally

Install the development tools once:

```powershell
python -m pip install -r requirements-dev.txt
```

Then run the same backend checks used by CI:

```powershell
python -m ruff check app tests
python -m pytest
pip-audit -r requirements-dev.txt
```

The tests use a temporary SQLite database per test and do not use `data/app.db`.
GitHub Actions runs backend lint/tests, audits Python dependencies for known vulnerabilities, and builds the frontend on pushes and pull requests.

### 2. Start the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. The page calls the example endpoint at `http://127.0.0.1:8000/api/hello` to show that the two servers can communicate.

The development servers bind to localhost. CORS allows only the two local frontend origins on port 5173. Do not expose either server to a network until authentication and HTTPS are configured.
