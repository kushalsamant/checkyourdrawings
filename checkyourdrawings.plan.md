# Check Your Drawings

AEC coordination tool: upload two architectural drawing PDFs (Drawing A and Drawing B), auto-align them, and download a color-coded coordination overlay as **PDF** (deliverable) or **PNG** (preview).

**Production:** live at https://checkyourdrawings.kvshvl.in — smoke verified 2026-06-20.

## Product tiers

| Tier | Access |
|------|--------|
| Anonymous | Unlimited single-pair `/compare` + Download PDF + Download PNG |
| Signed in, not paid | Same as anonymous; batch tab shows upgrade prompt |
| Paid kvshvl (`weekly` / `monthly` / `yearly`) | Batch UI + ZIP export of PDF overlays |

---

## Architecture

### Stack

```text
User laptop → upload → Render (compare, writes outputs/) → preview/download → user laptop
Vercel = UI only | Supabase = auth + batch billing | No output cloud storage
```

### Components

| Layer | Role |
|-------|------|
| `frontend/` | Upload UI, result viewer, metadata panel |
| `backend/app/routes/compare.py` | `POST /compare` — validate uploads, run pipeline |
| `backend/app/services/pdf_converter.py` | PyMuPDF rasterize PDF → RGB image |
| `backend/app/services/pdf_exporter.py` | Embed overlay PNG on Drawing A sheet PDF |
| `backend/app/services/alignment.py` | ORB features + RANSAC homography + optional ECC refinement |
| `backend/app/services/content_detection.py` | Ink bounding boxes, union crop, overlap gate |
| `backend/app/services/overlay_renderer.py` | Orange/blue/green/red ink map + footer band |
| `backend/outputs/` | Generated comparison PNG + PDF (served at `/outputs/`, pruned after 24h) |

### Request flow

```text
Drawing A PDF + Drawing B PDF
  → load_image (PyMuPDF)
  → align_drawing_b_to_a (ORB + RANSAC + optional ECC)
  → detect_content_bbox + union_bbox + compute_overlap_bbox (gate)
  → render_coordination_overlay (orange / blue / green / red)
  → comparison-{uuid}.png + comparison-{uuid}.pdf
```

### Alignment behavior

- **Hard fail (HTTP 400):** cannot compute homography, or insufficient overlapping ink between sheets.
- **Marginal (HTTP 200 + warning):** low inlier ratio — overlay still returned; footer notes low confidence.
- **Timeout (HTTP 504):** compare exceeds `CYD_COMPARE_TIMEOUT_SECONDS` (default 300s).

### Highest-risk code

- `backend/app/services/alignment.py` — homography quality drives usefulness
- `backend/app/services/overlay_renderer.py` — pixel classification semantics
- `backend/app/services/content_detection.py` — overlap gate rejects unrelated sheets

### Out of scope

- DWG, PNG, JPG, GIF inputs
- Comparison history / Supabase output storage — users download deliverables to their own systems

### Production topology

| Service | Host | Role |
|---------|------|------|
| Frontend | Vercel → `checkyourdrawings.kvshvl.in` | Static Vite build |
| API | Render → `checkyourdrawings.onrender.com` | FastAPI + OpenCV + PyMuPDF |
| Storage | Render ephemeral disk | `backend/outputs/` — PNG + PDF, pruned after 24h |

---

## Overlay semantics

Every ink pixel is classified:

| Color | Meaning |
|-------|---------|
| Orange | Ink only in Drawing A |
| Blue | Ink only in Drawing B |
| Green | Ink in both (aligned overlap) |
| Red | Misaligned overlap (clash) |

**Same file twice → mostly green.** That is correct for identical inputs.

**Coordination overlay colors (orange/blue/green/red) are drawing semantics, not UI chrome** — do not swap for kvshvl brand colors.

---

## kvshvl brand shell

Check Your Drawings should look like **kvshvl.in** — same colors, typography, and page chrome.

| Surface | Mechanism |
|---------|-----------|
| Compare app (`/`) | `frontend/src/App.tsx` + `styles.css` (`.app-shell`, `.app-footer`) |
| About page (`/about`) | `index.md` → build-time import → `frontend/src/pages/AboutPage.tsx` |
| Site chrome | `frontend/index.html` (meta, GA `G-JTHJJMRHT7`) |

**Vercel deploys from repo root** via [`vercel.json`](vercel.json) (`npm ci --prefix frontend`, output `frontend/dist`).

| Token (kvshvl.in) | Value |
|-------------------|--------|
| `--accent` | `#f12345` |
| `--text-primary` | `#888888` |
| `--text-muted` | `#aaaaaa` |
| `--background` | `#ffffff` |

**Source of truth for colors:** [`kushalsamant.github.io/assets/css/main.css`](../kushalsamant.github.io/assets/css/main.css)

**Portfolio link:** side tab CTA → `https://checkyourdrawings.kvshvl.in` in [`kushalsamant.github.io/_includes/side-tabs.html`](../kushalsamant.github.io/_includes/side-tabs.html)

---

## Repository layout

| Path | Purpose |
|------|---------|
| `backend/` | FastAPI app, compare pipeline, tests |
| `frontend/` | React UI (`/`, `/about`, `/auth/callback`) |
| `index.md` | About-page marketing copy (bundled at build into `/about`) |
| `supabase/` | Migrations (platform users; optional outputs bucket) |
| `scripts/` | See [Scripts](#scripts) below |
| Root config | `Dockerfile`, `render.yaml`, `vercel.json`, `.env.example`, `LICENSE` |

**Local-only at repo root (gitignored):** smoke PDFs `0A`/`0B`, `.env`, `.env.deploy.local`, comparison outputs

### Scripts

| File | Purpose |
|------|---------|
| `scripts/deploy_render_env.py` | Push production secrets from `.env.deploy.local` to Render |
| `scripts/smoke_production.py` | Hosted smoke — health, anonymous compare, authed compare |
| `scripts/enable_google_oauth.py` | Configure Google OAuth on the Supabase project |

**Root static utilities (not part of Vercel SPA deploy):**

| File | Notes |
|------|-------|
| `pinterest-bdc46.html` | **Do not delete** — Pinterest domain verification |
| `CNAME` | `checkyourdrawings.kvshvl.in` (GitHub Pages convention; production DNS is Vercel) |

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

Open **http://127.0.0.1:5173**. Leave `VITE_API_BASE_URL` unset (Vite proxies `/compare`, `/outputs`, `/health`).

### Environment variables

**Backend (`CYD_` prefix)** — see [`.env.example`](.env.example)

**Frontend** — see [frontend/.env.example](frontend/.env.example)

| Variable | Production value |
|----------|------------------|
| `CYD_CORS_ORIGINS` | `https://checkyourdrawings.kvshvl.in,https://www.checkyourdrawings.kvshvl.in` |
| `CYD_AUTH_REQUIRED` | `false` |
| `VITE_API_BASE_URL` | `https://checkyourdrawings.onrender.com` |
| `VITE_SUPABASE_URL` | `https://ytcnzhapqainbtkoshvh.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | (from Supabase dashboard) |
| `VITE_KVSHVL_UPGRADE_URL` | `https://kvshvl.in` |

---

## Deploy

| Surface | Value |
|---------|-------|
| Vercel project | `kvshvl/checkyourdrawings` |
| Frontend URL | https://checkyourdrawings.kvshvl.in |
| API URL (live) | https://checkyourdrawings.onrender.com |
| API custom domain | `api.checkyourdrawings.kvshvl.in` — **optional, DNS not configured** |

### Render (API)

Blueprint: [`render.yaml`](render.yaml)

**Required production env:**

| Key | Value |
|-----|-------|
| `CYD_AUTH_REQUIRED` | `false` |
| `CYD_CORS_ORIGINS` | `https://checkyourdrawings.kvshvl.in,https://www.checkyourdrawings.kvshvl.in` |

Outputs are served from Render disk at `/outputs/` (PNG preview + PDF deliverable). Supabase is auth + batch billing only.

Apply env from local secrets. For freemium, `CYD_AUTH_REQUIRED` must be `false` in `.env.deploy.local` before running:

```powershell
.\.venv\Scripts\python.exe scripts\deploy_render_env.py
```

Or set keys manually in Render → **checkyourdrawings-api** → **Environment**.

Validate blueprint:

```powershell
render blueprints validate ./render.yaml
```

### Vercel (frontend)

Root [`vercel.json`](vercel.json) runs `npm ci --prefix frontend` and builds `frontend/dist`.

`AboutPage` imports root [`index.md`](index.md), so git-connected deploys must include the full repo.

```powershell
cd C:\Users\ADMIN\Documents\GitHub\checkyourdrawings
vercel --prod --yes
```

### DNS

| Record | Points to |
|--------|-----------|
| `checkyourdrawings.kvshvl.in` | Vercel |
| `api.checkyourdrawings.kvshvl.in` | Render (optional — not configured) |

Quick checks:

```powershell
curl.exe https://checkyourdrawings.onrender.com/health
curl.exe https://checkyourdrawings.kvshvl.in
```

---

## Testing

### Backend

```powershell
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
pytest backend/tests -v
```

| Area | Coverage |
|------|----------|
| `/compare` integration | PDF-only uploads, content scenarios, margin shift |
| Route errors | 415 for non-PDF, 400 empty/corrupt, 413 oversize |
| Pipeline units | alignment, overlay renderer, content detection, image limits, output cleanup |

Tests marked `@pytest.mark.integration` use synthetic PDF fixtures from `backend/tests/fixtures/factory.py`.

### Frontend

```powershell
cd frontend
npm test
```

Covers PDF-only file validation and API response parsing.

---

## Smoke tests

### Local smoke

Keep smoke PDFs at **repo root** (gitignored):

| File | Role |
|------|------|
| `0A 02-Saurabh mishraR2-Model.pdf` | Drawing A |
| `0B 02-Saurabh mishraR2-Model.pdf` | Drawing B |

| # | Step | Expected |
|---|------|----------|
| 1 | Upload `0A` / `0B` | Both accepted (PDF only) |
| 2 | **Compare** | Completes in under ~30s |
| 3 | Result image | Green where sheets match; orange/blue at changes; red at misaligned edges |
| 4 | Footer | Drawing A/B filenames, timestamp, color legend |
| 5 | Metadata | Orange/blue/green/red counts; alignment confidence `high` or `marginal` |
| 6 | **Download PDF** and **Download PNG** | Files save and open |
| 7 | Same file trap | Same PDF twice → mostly green |
| 8 | Invalid file | `.png` or `.dwg` → client-side or 415 error |

**Common mistakes:**

- Opening `:8000` in the browser — JSON API only; use `:5173`
- Comparing unrelated PDFs — alignment fails with HTTP 400 (by design)

**Cross-floor compares:** pairs like `1A` vs `2A` show high change ratios (~60%+) with high alignment confidence — expected when comparing different floors, not a pipeline bug. Use same letter pairs (`0A`/`0B`, `1A`/`1B`) for smoke sign-off.

Optional API curl:

```powershell
curl -X POST http://127.0.0.1:8000/compare `
  -F "drawing_a=@C:\path\to\drawing-a.pdf" `
  -F "drawing_b=@C:\path\to\drawing-b.pdf"
```

### Hosted smoke

| # | Step | Expected |
|---|------|----------|
| H1 | [kvshvl.in](https://www.kvshvl.in) → **Check Your Drawings** side tab | Lands on `checkyourdrawings.kvshvl.in` |
| H2 | Page styling | kvshvl palette: red accent `#f12345`, gray text, white background |
| H3 | Upload `0A` / `0B` → **Compare** | Overlay renders |
| H4 | **Download PDF** and **Download PNG** | Files save and open |
| H5 | `curl https://checkyourdrawings.onrender.com/health` | `"status":"ok"` |
| H6 | Compare from production frontend | No CORS error |

Anonymous compare returns **200** without `Authorization`. Paid batch tab unlocks after `/account` reports `paid: true`.

`scripts/smoke_production.py` authed compare expects `/outputs/` PNG + PDF paths on Render.

### Production sign-off log

| Date | Commit | Result |
|------|--------|--------|
| 2026-06-20 | `f854e7f` + `22c3c2a` | **Pass** — anonymous browser smoke: compare, Download PDF/PNG |
| 2026-06-20 | `40db813` | **Pass** — automated checks below |

| # | Check | Result |
|---|-------|--------|
| P1 | `GET /health` | `{"status":"ok"}` |
| P2 | `GET /health/ready` | `auth_required: false` |
| P3 | `GET /account` (no auth) | `signed_in: false`, `paid: false` |
| P4 | `POST /compare` (synthetic PDFs, no auth) | **200** ~14s |
| P5 | CORS preflight from `checkyourdrawings.kvshvl.in` | **200** |
| P6 | Frontend `https://checkyourdrawings.kvshvl.in` | **200** |
| P7 | `/about` | **200** |

**Manual still recommended:** upload real `0A`/`0B` in browser, confirm overlay + downloads, batch tab upsell for unsigned user.

---

## Manual operations

Tasks outside repo code — Google Cloud, contacts, or DNS.

### Google OAuth consent screen branding

Google may show `ytcnzhapqainbtkoshvh.supabase.co` on sign-in. Branding improves trust until unified kvshvl.in sign-in ships.

1. [Google Cloud Console](https://console.cloud.google.com/) → project with **KVSHVL (Production)** OAuth client
2. **APIs & Services** → **OAuth consent screen**
3. Set app name `KVSHVL`, logo, homepage `https://kvshvl.in`, authorized domains `kvshvl.in`, `checkyourdrawings.kvshvl.in`
4. Test sign-in from https://checkyourdrawings.kvshvl.in

The Supabase callback host may still appear on one line of the Google prompt while CYD uses per-app Supabase OAuth.

### Friend share outreach

**URL:** https://checkyourdrawings.kvshvl.in

> I built a small tool for coordination — upload two drawing PDFs (revision A vs B) and get a color overlay in ~30 seconds. Free for single pairs, no sign-in.
>
> https://checkyourdrawings.kvshvl.in
>
> If you ever run a full revision stack (10+ pairs), there is a batch mode behind kvshvl subscription — I'd love to know if that would save you time and what you'd pay from project budget.

### Optional API custom domain

Skip (onrender.com is fine), **or** CNAME `api.checkyourdrawings.kvshvl.in` → Render, then update `VITE_API_BASE_URL` and `CYD_CORS_ORIGINS`.

---

## Auth and batch

Freemium single compare is live (`CYD_AUTH_REQUIRED=false`). Paid batch uses sign-in + kvshvl subscription gate (402 for batch) — reads platform `users` table; **no Razorpay in CYD**.

**Optional env (batch sign-in only):** `PLATFORM_DATABASE_URL`, `SUPABASE_*` on Render; `VITE_SUPABASE_*` on Vercel. Run `scripts/deploy_render_env.py` from `.env.deploy.local` when updating secrets. Enable Google OAuth via `scripts/enable_google_oauth.py`.

**Auth code (batch only):**

| Area | Files |
|------|-------|
| JWT + deps + subscription | `backend/app/auth/`, `backend/app/subscription/` |
| Platform DB + User model | `backend/app/database.py`, `backend/app/models/user.py` |
| Frontend auth | `frontend/src/lib/auth-provider.tsx`, `frontend/src/pages/AuthCallback.tsx` |

### Unified kvshvl.in sign-in (deferred)

**Status:** Not implemented. CYD uses per-app Supabase OAuth today.

**Target (requires kvshvl.in repo):**

1. CYD **Sign in** redirects to `https://kvshvl.in/sign-in?return_to=...`
2. kvshvl completes Google OAuth once
3. Return to CYD with platform JWT (`backend/app/auth/jwt.py`)
4. Remove CYD frontend `signInWithOAuth` via per-app Supabase

---

## Dropped / do not restore

| Item | Status |
|------|--------|
| Server-side watermark | Removed (`40db813`) |
| Supabase compare output storage + `CYD_STORAGE_BYPASS` | Declined — download-first (`f854e7f`) |
| `storage.py`, comparison history UI | Removed |
| Full Sketch2BIM SaaS port | Declined |
| CLI install + login setup | Done |

---

## References

- kvshvl site: [`../kushalsamant.github.io`](../kushalsamant.github.io)
- Sketch2BIM deploy reference (gunicorn pattern): [`../sketch2bim/render.yaml`](../sketch2bim/render.yaml)
