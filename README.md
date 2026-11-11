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

FastAPI's interactive API docs are at <http://127.0.0.1:8000/docs>.

### 2. Start the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. The page calls the example endpoint at `http://127.0.0.1:8000/api/hello` to show that the two servers can communicate.

The development servers bind to localhost. CORS allows only the two local frontend origins on port 5173. Do not expose either server to a network until authentication and HTTPS are configured.
