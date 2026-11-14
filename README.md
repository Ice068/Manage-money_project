# Income & Expense Tracker

Personal web app for tracking income, expenses, savings, and purchase goals. The frontend and backend run as separate development servers.

## Stack

- Frontend: Vite, HTML, CSS, and JavaScript (`http://127.0.0.1:5173`)
- Backend: FastAPI and Uvicorn (`http://127.0.0.1:8000`)
- Database: SQLite
- Optional AI: OpenAI Responses API, called by the backend only

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
- `GET /api/dashboard/summary` — summarize a date range and estimate reserve days
- `GET /api/dashboard/settings` — read opening balance settings
- `PUT /api/dashboard/settings` — save opening balance and its effective date
- `GET /api/savings-goals` — list goals with progress and forecast
- `POST /api/savings-goals` — create a savings goal
- `GET /api/savings-goals/{id}` — read one goal
- `PUT /api/savings-goals/{id}` — replace a goal
- `DELETE /api/savings-goals/{id}` — delete a goal
- `GET /api/ai/status` — report whether AI is configured (never returns the key)
- `POST /api/ai/insights` — explain calculated dashboard values and an optional savings goal

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

The SQLite database is created at `data/app.db` the first time the backend starts unless `DATABASE_URL` points to PostgreSQL. This file is ignored by Git. `/api/exports/backup.json` downloads a portable backup of transactions, savings goals, and opening-balance settings; `/api/exports/transactions.csv` downloads the transactions as a spreadsheet-friendly CSV.

The dashboard summarizes income and expenses over an inclusive date range. It calculates current balance as the opening balance plus income minus expenses from the opening-balance date through today. Reserve days use average expenses per calendar day in the selected range; days without transactions count as zero spending. If the range has no expenses, the dashboard says it cannot estimate reserve days.

Savings-goal forecasts use the average net savings per calendar day from the opening-balance date through today. The estimate is shown only when net savings are positive; it is a historical estimate, not a guarantee. Each goal stores its target amount, amount already saved, and an optional note.

## Optional AI setup

Copy `.env.example` to `.env`, add your own `OPENAI_API_KEY`, and restart the backend. You can change `OPENAI_MODEL` if your API project uses a different model. Never commit `.env`; it is ignored by Git. The AI feature stays disabled without a key.

AI runs only after you press an explanation button. The backend computes the financial values and sends only dates and aggregate numbers to OpenAI; it does not send transaction records, categories, notes, goal names, or goal notes. Requests set `store=false`, but OpenAI's abuse-monitoring logs may retain prompts and responses for up to 30 days. OpenAI says API data is not used to train models by default. Tests mock the OpenAI client and never make a real API call.

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

## Free Render deployment

The Render Blueprint in `render.yaml` deploys one Docker web service on the Free plan. It serves the built frontend and FastAPI from the same origin, and enables a single-user login in production. The app requires `APP_USERNAME`, an Argon2id `APP_PASSWORD_HASH`, `APP_SECRET_KEY`, and `DATABASE_URL` before production startup; API docs are disabled in production. Sessions use an HTTP-only, Secure, SameSite=Strict cookie, expire after 12 hours, and API writes require a same-origin request.

Render Free has an ephemeral filesystem. Local SQLite files would disappear after restart, sleep, or redeploy, so do not point the deployed app at SQLite. For the selected $0 setup, use a Supabase Free PostgreSQL project and its shared **session pooler** connection string as `DATABASE_URL`. Session mode uses IPv4 and supports persistent-backend connections; copy the exact host and username from the Supabase Connect dialog, use port 5432, and require TLS with `sslmode=require`. The app creates its tables at startup. Supabase Free includes 500 MB of database storage, may pause projects after a week of low activity, and has no automatic database backups. Render Free services sleep after 15 minutes without traffic and can take about a minute to wake. Keep an off-site JSON backup using the in-app export. Create both services in Singapore for lower latency. See [Render Free service limits](https://render.com/docs/free), [Supabase Free plan limits](https://supabase.com/pricing), [Supabase project pausing](https://supabase.com/docs/guides/platform/free-project-pausing), [Supabase connection methods](https://supabase.com/docs/guides/database/connecting-to-postgres), and [available regions](https://supabase.com/docs/guides/platform/regions).

Deployment steps:

1. Create a Supabase Free project in Southeast Asia (Singapore). In **Connect**, choose **Session pooler** and copy the PostgreSQL connection string; make sure it includes `sslmode=require`. Do not put this secret in Git or send it in chat. Keep Supabase and Render in Singapore to reduce connection latency.
2. Generate an app password hash locally with `python tools/hash_password.py`. The script asks for a password without echoing it and prints an Argon2id hash. Use a unique password of at least 12 characters.
3. In Render, create a Blueprint from this repository and select the `main` branch. Keep the web service plan set to `free`.
4. In the Render service's environment settings, set `APP_USERNAME`, `APP_PASSWORD_HASH`, and `DATABASE_URL`. Render generates `APP_SECRET_KEY` from the Blueprint. The Blueprint leaves `OPENAI_API_KEY` unset to avoid paid AI API usage.
5. Wait for the deploy to become healthy, then open the Render URL and log in. The deployed database starts empty; local SQLite data remains on your machine. Do not upload it unless you explicitly choose to transfer that private data to Supabase.

This is a free hobby deployment, not a production-grade financial datastore: the app may sleep, Supabase can pause after inactivity, and the Free plan has no automatic backups. Keep your own JSON backups. The AI feature stays unavailable unless you add an API key, which can incur usage charges.
