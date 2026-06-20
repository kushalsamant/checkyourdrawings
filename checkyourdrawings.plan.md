---
name: Check Your Drawings — Master Plan
overview: "Pass 1 + optional auth code shipped in repo. Pass 2 = hosted MVP at checkyourdrawings.kvshvl.in. Pass 3 = freemium compare + paid batch (commit 40db813 on main)."
todos:
  - id: kvshvl-brand-colors
    content: "kvshvl brand shell in React (styles.css, App.tsx, AboutPage from index.md, GA in index.html)"
    status: completed
  - id: dockerfile-render
    content: "Production Dockerfile + render.yaml; deploy API on Render (gunicorn timeout 300s, CYD_CORS_ORIGINS, auth bypass env)"
    status: completed
  - id: vercel-frontend
    content: "Vercel config + deploy frontend; VITE_API_BASE_URL → Render API; domain checkyourdrawings.kvshvl.in"
    status: completed
  - id: hosted-smoke
    content: "Smoke-test live site from kvshvl.in side tab; document hosted checklist in docs/smoke-test.md"
    status: completed
isProject: true
---

# Check Your Drawings — Master Plan

Canonical plan for the repo. AEC coordination tool for comparing two architectural drawing PDFs. Upload Drawing A and Drawing B (plotted or exported from your design software), auto-align them, and download a coordination overlay PNG.

**Work one task at a time** (see frontmatter todos). **Pass 2 complete** — production smoke verified 2026-06-20 (`40db813`).

**Current product tiers:**

| Tier | Access |
|------|--------|
| Anonymous | Unlimited single-pair `/compare` + full PNG download |
| Signed in, not paid | Same as anonymous; batch tab shows upgrade prompt |
| Paid kvshvl | Batch queue + ZIP export |

---

## kvshvl.in brand shell (Pass 2)

Check Your Drawings should look like **kvshvl.in** — same colors, typography, and page chrome.

### Layout (React SPA)

| Surface | Mechanism |
|---------|-----------|
| Compare app (`/`) | `frontend/src/App.tsx` + `styles.css` (`.app-shell`, `.app-footer`) |
| About page (`/about`) | `index.md` → build-time import → `frontend/src/pages/AboutPage.tsx` |
| Site chrome | `frontend/index.html` (meta, GA `G-JTHJJMRHT7`) |

**Vercel deploys from repo root** via [`vercel.json`](vercel.json) (`npm ci --prefix frontend`, output `frontend/dist`). No Jekyll at repo root. Pinterest verify HTML (`pinterest-bdc46.html`) is a static utility, not the live product shell.

**Brand shell mapping:**

| Pattern | CYD equivalent |
|---------|----------------|
| `:root` CSS variables | `frontend/src/styles.css` |
| `<main>{{ content }}</main>` | `.app-shell` in `App.tsx`; `.landing-shell` on `/about` |
| `<footer>© year title</footer>` | `.app-footer` in `App.tsx` and `AboutPage.tsx` |
| Narrow prose column (`72ch`) | `.landing-shell` on `/about` only |
| Google Analytics in `<head>` | `frontend/index.html` (`G-JTHJJMRHT7`) |

**Source of truth for colors:** [`kushalsamant.github.io/assets/css/main.css`](../kushalsamant.github.io/assets/css/main.css) (canonical kvshvl tokens).

**Layout/structure reference:** `frontend/src/App.tsx`, `frontend/src/pages/AboutPage.tsx`, `frontend/src/styles.css`.

> **Note:** Use **kvshvl.in token meanings** in `styles.css` (`--accent` = red, `--text-muted` = gray).

| Token (kvshvl.in) | Value |
|-------------------|--------|
| `--accent` | `#f12345` |
| `--text-primary` | `#888888` |
| `--text-muted` | `#aaaaaa` |
| `--background` | `#ffffff` |

**Keep unchanged:** coordination overlay colors (orange/blue/green/red) — drawing semantics, not UI chrome.

**Status:** `kvshvl-brand-colors` — **Done** (includes `/about` from `index.md`).

---

## Overlay semantics

The coordination overlay paints every ink pixel:

| Color | Meaning |
|-------|---------|
| Orange | Ink only in Drawing A |
| Blue | Ink only in Drawing B |
| Green | Ink in both (aligned overlap) |
| Red | Misaligned overlap (clash) |

**Same file twice → mostly green.** That is correct behavior for identical inputs.

---

## Already complete (do not redo)

### Pass 1 — compare product

- PDF pipeline, React UI, FastAPI backend, tests, local smoke on `0A`/`0B`
- Docs: [architecture.md](docs/architecture.md), [smoke-test.md](docs/smoke-test.md), [testing.md](docs/testing.md)

### kvshvl.in marketing

| Item | Status |
|------|--------|
| Side tab CTA → `https://checkyourdrawings.kvshvl.in` | **Live** in [`kushalsamant.github.io/_includes/side-tabs.html`](../kushalsamant.github.io/_includes/side-tabs.html) |
| Repo [`CNAME`](CNAME) | `checkyourdrawings.kvshvl.in` |

### Dev machine setup

| Item | Status |
|------|--------|
| Vercel CLI (`vercel whoami` → `kushalsamant`) | **Done** |
| Render CLI + login | **Done** |
| Render binary | `%LOCALAPPDATA%\Programs\cli-bin\render.exe` (user PATH) |

### Repo config and dependencies (former `production-config` task)

| Item | File | Status |
|------|------|--------|
| `gunicorn` + Pass 3 deps | [backend/requirements.txt](backend/requirements.txt) | **Done** |
| Dual `Settings` + bypass flags | [backend/app/config.py](backend/app/config.py) | **Done** — defaults: `auth_required=false`, `storage_bypass=true` |
| Production env docs | [`.env.example`](.env.example), [frontend/.env.example](frontend/.env.example) | **Done** |
| `/health` + `/health/ready` | [backend/app/main.py](backend/app/main.py) | **Done** |
| `VITE_API_BASE_URL` production build path | [frontend/src/services/api.ts](frontend/src/services/api.ts) | **Done** |

### Optional auth/storage code (landed, **not enabled** — Pass 3)

Code exists but is **off by default**. Pass 2 deploy does **not** need platform DB or Supabase env vars.

| Area | Files |
|------|-------|
| JWT + deps + subscription utils | `backend/app/auth/`, `backend/app/subscription/` |
| Platform DB + models | `backend/app/database.py`, `backend/app/models/` |
| Supabase storage + compare metadata | `backend/app/services/storage.py`, wired in [compare.py](backend/app/routes/compare.py) |
| Supabase migration | [supabase/migrations/20260617015123_create_cyd_outputs_bucket.sql](supabase/migrations/20260617015123_create_cyd_outputs_bucket.sql) |
| Frontend auth (only shows if `VITE_SUPABASE_*` set) | `frontend/src/lib/auth-provider.tsx`, `frontend/src/pages/AuthCallback.tsx`, `@supabase/supabase-js` |

**Production defaults for free hosted MVP** (set on Render / leave unset on Vercel):

```
CYD_AUTH_REQUIRED=false
CYD_STORAGE_BYPASS=true
CYD_CORS_ORIGINS=https://checkyourdrawings.kvshvl.in,https://www.checkyourdrawings.kvshvl.in
```

Do **not** set `PLATFORM_DATABASE_URL`, `SUPABASE_*`, or `VITE_SUPABASE_*` until Pass 3.

---

## Repository layout

| Path | Purpose |
|------|---------|
| `backend/` | FastAPI app, compare pipeline, tests |
| `frontend/` | React UI (`/`, `/about`, `/auth/callback`) |
| `index.md` | About-page copy (bundled at build into `/about`) |
| `docs/` | Architecture, testing, smoke-test docs |
| `supabase/` | Pass 3 migrations (not required for Pass 2 deploy) |
| Root config | `checkyourdrawings.plan.md`, `LICENSE`, `Dockerfile`, `.gitignore`, `.env.example` |

**Local-only at repo root (gitignored):** smoke PDFs `0A`/`0B`, `.env`

**Root static utilities (not part of Vercel SPA deploy):** `pinterest-bdc46.html` (Pinterest domain verify)

---

## Local development

```powershell
# Terminal 1 — API
cd C:\Users\ADMIN\Documents\GitHub\checkyourdrawings
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload

# Terminal 2 — UI
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173**. Leave `VITE_API_BASE_URL` unset (Vite proxies `/compare` and `/outputs`).

### Environment variables

**Backend (`CYD_` prefix)** — see [`.env.example`](.env.example). Key production var:

| Variable | Pass 2 production value |
|----------|-------------------------|
| `CYD_CORS_ORIGINS` | `https://checkyourdrawings.kvshvl.in,https://www.checkyourdrawings.kvshvl.in` |

**Frontend** — see [frontend/.env.example](frontend/.env.example):

| Variable | Pass 2 production value |
|----------|-------------------------|
| `VITE_API_BASE_URL` | `https://checkyourdrawings.onrender.com` (`api.checkyourdrawings.kvshvl.in` optional — DNS not live) |

---

## Pass 2 — Hosted MVP (current work)

**Goal:** Ship the free compare tool to `checkyourdrawings.kvshvl.in`. No login, no billing.

**Pass 2 status:** live at `checkyourdrawings.kvshvl.in`; production smoke verified 2026-06-20 (`40db813`).

| Item | Status |
|------|--------|
| kvshvl.in brand shell in React | **Done** |
| [Dockerfile](Dockerfile) + [render.yaml](render.yaml) | **Done** |
| Root [`vercel.json`](vercel.json) | **Done** |
| Live deploy + DNS | **Done** |
| Hosted smoke (production) | **Done** — [docs/smoke-test.md](docs/smoke-test.md) |
| Freemium compare + batch UI | **Done** — `CYD_AUTH_REQUIRED=false` on Render |

### Production architecture

```mermaid
flowchart LR
  subgraph kvshvl [kvshvl.in]
    SideTab[Side tab CTA]
  end
  subgraph prod [Production]
    Vercel[Vercel frontend]
    Render[Render API]
    Disk[Ephemeral outputs disk]
  end
  User[Visitor] --> SideTab
  SideTab -->|checkyourdrawings.kvshvl.in| Vercel
  Vercel -->|POST /compare and GET /outputs| Render
  Render -->|POST /compare| Disk
```

| Service | Host | Role |
|---------|------|------|
| Frontend | Vercel → `checkyourdrawings.kvshvl.in` | Static Vite build |
| API | Render → `checkyourdrawings.onrender.com` | FastAPI + OpenCV + PyMuPDF |
| Storage | Render ephemeral disk | `backend/outputs/` — pruned after 24h |

**Reference:** [`sketch2bim/render.yaml`](../sketch2bim/render.yaml) for gunicorn pattern only.

### Pass 2 tasks (remaining)

#### 0. kvshvl brand shell (`kvshvl-brand-colors`) — **Done**

- [frontend/src/styles.css](frontend/src/styles.css) — kvshvl `:root` tokens; `.landing-shell` for `/about`
- [frontend/src/App.tsx](frontend/src/App.tsx) — `.app-shell` + `.app-footer`; footer link to `/about`
- [frontend/src/pages/AboutPage.tsx](frontend/src/pages/AboutPage.tsx) — renders [index.md](index.md) at `/about`
- [frontend/index.html](frontend/index.html) — meta description, GA `G-JTHJJMRHT7`

#### 1. API on Render (`dockerfile-render`)

- Replace placeholder [Dockerfile](Dockerfile): `python:3.12-slim`, OpenCV system libs, `gunicorn` + uvicorn worker, `--timeout 300`
- Create `render.yaml` with `healthCheckPath: /health`
- Render env vars:
  - `CYD_CORS_ORIGINS=https://checkyourdrawings.kvshvl.in,https://www.checkyourdrawings.kvshvl.in`
  - `CYD_AUTH_REQUIRED=false`
  - `CYD_STORAGE_BYPASS=true`
- Connect repo on Render; deploy API

#### 2. Frontend on Vercel (`vercel-frontend`)

- Root [`vercel.json`](vercel.json): `npm ci --prefix frontend`, build `frontend/dist`
- Env at build time: `VITE_API_BASE_URL=https://checkyourdrawings.onrender.com`
- Connect repo on Vercel; add custom domain `checkyourdrawings.kvshvl.in`

**DNS:**

| Record | Points to |
|--------|-----------|
| `checkyourdrawings.kvshvl.in` | Vercel |
| `api.checkyourdrawings.kvshvl.in` | Render (optional — not configured; use `*.onrender.com`) |

#### 3. Hosted smoke test (`hosted-smoke`)

Add section to [docs/smoke-test.md](docs/smoke-test.md):

1. Open [kvshvl.in](https://www.kvshvl.in) → **Check Your Drawings** side tab
2. Upload `0A` / `0B` → Compare → overlay renders
3. Download PNG works
4. `curl https://api.../health` → `{"status":"ok"}`

**Estimated effort:** ~1 day (deploy files + dashboard setup + smoke).

---

## Pass 3 — Auth, batch, and cloud storage (shipped for freemium + paid batch)

Most code is **already in the repo** and **live** for freemium single compare. Paid batch uses sign-in + kvshvl subscription gate.

**Production (freemium):**

```
CYD_AUTH_REQUIRED=false
CYD_STORAGE_BYPASS=true
```

**When enabling full cloud persistence for paid users:**

- Set `CYD_STORAGE_BYPASS=false` on Render
- Set `PLATFORM_DATABASE_URL`, `SUPABASE_*` on Render; `VITE_SUPABASE_*` on Vercel
- Run Supabase migration; configure OAuth redirect URLs
- Ensure `.env.pass3.local` has `CYD_AUTH_REQUIRED=false` before `scripts/deploy_pass3_env.py`

kvshvl subscription gate (402 for batch) — reads platform `users` table; **no Razorpay in CYD**.

**Deferred:** unified kvshvl.in sign-in (requires kvshvl.in repo) — see [docs/deploy.md](docs/deploy.md).

**Removed:** server-side watermark on free PNGs (`40db813`) — paid differentiation is batch + ZIP only.

---

## Dropped / complete (do not resurrect)

| Former plan | Status |
|-------------|--------|
| Pass 1 smoke test | Done |
| Red → orange / magenta → red clash | Shipped |
| kvshvl.in side tab CTA | Done |
| Config + gunicorn + `.env.example` | Done |
| Auth/storage code scaffold | Done (disabled by default) |
| kvshvl brand shell | Done |
| Full Sketch2BIM SaaS port | Declined |
| CLI install + login | Done |

---

## References

- Architecture: [docs/architecture.md](docs/architecture.md)
- kvshvl site: [`../kushalsamant.github.io`](../kushalsamant.github.io)
- Sketch2BIM deploy reference: [`../sketch2bim/render.yaml`](../sketch2bim/render.yaml)
