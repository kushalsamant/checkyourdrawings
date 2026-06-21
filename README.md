# Check Your Drawings

Compare two architectural drawing PDFs and get an auto-aligned coordination overlay (PNG + PDF).

**Production:** [checkyourdrawings.kvshvl.in](https://checkyourdrawings.kvshvl.in) (frontend on Vercel) · API on Render

## Repo layout

| Path | Role |
|------|------|
| [frontend/](frontend/) | React + Vite UI |
| [backend/](backend/) | FastAPI compare API (async jobs + Bunny outputs) |
| [index.md](index.md) | About page content (rendered at `/about`) |
| [migrations/](migrations/) | Postgres job queue schema |
| [auth](https://github.com/kushalsamant/auth) (separate repo) | Google sign-in at `auth.kvshvl.in` |
| [platform-api](https://github.com/kushalsamant/platform-api) | Accounts, entitlements, Razorpay |

## Product

- Upload **Drawing A** and **Drawing B** (PDF only).
- Compare runs as an **async job**; the UI polls until the overlay is ready.
- Sign-in via `auth.kvshvl.in`; account and billing on **platform-api**.
- Outputs stored on **Bunny CDN** (~24h signed URLs).

See [index.md](index.md) for user-facing copy on the About page.

## Local development

**Backend** (port 8000):

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt -r backend\requirements-dev.txt
$env:PYTHONPATH = (Get-Location).Path
$env:PLATFORM_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/checkyourdrawings"
python scripts\migrate.py
.\.venv\Scripts\uvicorn backend.app.main:app --reload --port 8000
```

**Frontend** (port 5173):

```powershell
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 — Vite proxies API routes to the backend. Details: [frontend/README.md](frontend/README.md).

Copy env from [env.example](env.example) into `.env.deploy.local` (never commit real secrets).

## Tests

```powershell
# Backend (from backend/)
..\.venv\Scripts\pytest -q

# Frontend (from frontend/)
npm test
```

CI runs both on push/PR (see [.github/workflows/ci.yml](.github/workflows/ci.yml)).

## Deploy

- **API:** Render (Docker) → `checkyourdrawings.onrender.com`
- **Frontend:** Vercel → `checkyourdrawings.kvshvl.in`
- **Platform:** `platform-api-1y5i.onrender.com`
- **Auth:** `auth.kvshvl.in`

More detail: [backend/README.md](backend/README.md).
