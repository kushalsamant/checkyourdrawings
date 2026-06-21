# Check Your Drawings

Compare two architectural drawing PDFs and get an auto-aligned coordination overlay (PNG + PDF).

**Production:** [checkyourdrawings.kvshvl.in](https://checkyourdrawings.kvshvl.in) (frontend on Vercel) · API on Render

## Repo layout

| Path | Role |
|------|------|
| [frontend/](frontend/) | React + Vite UI |
| [backend/](backend/) | FastAPI compare API |
| [index.md](index.md) | About page content (rendered at `/about`) |
| [supabase/migrations/](supabase/migrations/) | Postgres schema for user accounts |
| [auth](https://github.com/kushalsamant/auth) (separate repo) | Google sign-in at `auth.kvshvl.in` |

## Product (current)

- Upload **Drawing A** and **Drawing B** (PDF only); no sign-in required to compare.
- Fair-use **rate limits** on `/compare` protect the service from abuse.
- Optional sign-in links your session for account status (paid tier wiring is planned).
- Results live on the server ~24h; download PNG/PDF to keep a copy.

See [index.md](index.md) for user-facing copy on the About page.

## Local development

**Backend** (port 8000):

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt -r backend\requirements-dev.txt
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\uvicorn backend.app.main:app --reload --port 8000
```

**Frontend** (port 5173):

```powershell
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 — Vite proxies API routes to the backend. Details: [frontend/README.md](frontend/README.md).

Copy env from [.env.example](.env.example) (never commit real secrets).

## Tests

```powershell
# Backend (from backend/)
..\.venv\Scripts\pytest -q

# Frontend (from frontend/)
npm test
```

CI runs both on push/PR (see [.github/workflows/ci.yml](.github/workflows/ci.yml)).

## Deploy

- **API:** Render (`render.yaml`, Docker) → `checkyourdrawings.onrender.com`
- **Frontend:** Vercel (`vercel.json`) → `checkyourdrawings.kvshvl.in`
- **Auth:** separate Vercel project → `auth.kvshvl.in`

More detail: [backend/README.md](backend/README.md).
