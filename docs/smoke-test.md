# Smoke test checklist

Manual sign-off for Pass 1. Use architectural PDF pairs plotted from your design software.

## Prerequisites

```powershell
# Terminal 1 — API
cd C:\Users\ADMIN\Documents\GitHub\checkyourdrawings
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --reload

# Terminal 2 — UI
cd frontend
npm run dev
```

Open **http://127.0.0.1:5173**

## Smoke PDF location

Keep the smoke PDFs at the **repo root** (gitignored). Paths below are relative to the project root.

## Required smoke pair

| File | Role |
|------|------|
| `0A 02-Saurabh mishraR2-Model.pdf` | Drawing A |
| `0B 02-Saurabh mishraR2-Model.pdf` | Drawing B |

## Checklist

| # | Step | Expected | Pass |
|---|------|----------|------|
| 1 | Upload `0A` as Drawing A, `0B` as Drawing B | Both accepted (PDF only) | |
| 2 | Click **Compare** | Completes in under ~30s | |
| 3 | Result image | **Green** where sheets match; **orange** and **blue** at real changes; **red** at misaligned edges if visible | |
| 4 | Footer | Drawing A/B filenames, timestamp, color legend | |
| 5 | Metadata | Orange/blue/green/red counts > 0 where expected; alignment confidence `high` or `marginal` | |
| 6 | **Download** | PNG saves and opens | |
| 7 | **Same file trap** | Upload same PDF twice → mostly **green** (correct for identical inputs) | |
| 8 | **Invalid file** | Try `.png` or `.dwg` → clear client-side or 415 error | |

## Overlay semantics

- **Orange** = ink only in A  
- **Blue** = ink only in B  
- **Green** = ink in both (aligned)  
- **Red** = clash (misaligned overlap)  

## API curl (optional)

```powershell
curl -X POST http://127.0.0.1:8000/compare `
  -F "drawing_a=@C:\path\to\drawing-a.pdf" `
  -F "drawing_b=@C:\path\to\drawing-b.pdf"
```

## Common mistakes

- Opening `:8000` in the browser — that is JSON API only; use `:5173`.
- Comparing **same file twice** and expecting orange/blue — all green is correct.
- Comparing unrelated PDFs — alignment fails with HTTP 400 (by design).

---

## Hosted smoke test (Pass 2)

Sign-off after deploy to Vercel + Render. Production URLs:

| Service | URL |
|---------|-----|
| Frontend | https://checkyourdrawings.kvshvl.in |
| API | https://checkyourdrawings.onrender.com (`api.checkyourdrawings.kvshvl.in` optional — DNS not live) |

### Prerequisites

- Render service live with `CYD_AUTH_REQUIRED=false`
- Vercel build has `VITE_API_BASE_URL` pointing at the Render API URL
- DNS: `checkyourdrawings.kvshvl.in` → Vercel, `api.checkyourdrawings.kvshvl.in` → Render (optional at first deploy)

### Checklist

| # | Step | Expected | Pass |
|---|------|----------|------|
| H1 | Open [kvshvl.in](https://www.kvshvl.in) → **Check Your Drawings** side tab | Lands on `checkyourdrawings.kvshvl.in` | |
| H2 | Page styling | kvshvl palette: red accent `#f12345`, gray text, white background | |
| H3 | Upload `0A` / `0B` smoke PDFs → **Compare** | Completes; overlay renders | |
| H4 | **Download PDF** and **Download PNG** | Files save and open | |
| H5 | API health | `curl https://<api-url>/health` returns `"status":"ok"` | |
| H6 | CORS | Compare works from production frontend (no browser CORS error) | |

### Production env reference

**Render:**

```
CYD_AUTH_REQUIRED=false
CYD_CORS_ORIGINS=https://checkyourdrawings.kvshvl.in,https://www.checkyourdrawings.kvshvl.in
```

**Vercel (build time):**

```
VITE_API_BASE_URL=https://checkyourdrawings.onrender.com
```

---

## Production sign-off log

| Date | Commit | Result |
|------|--------|--------|
| 2026-06-20 | `40db813` (watermark removed) | **Pass** — automated checks below |

### Automated checks (2026-06-20, commit `40db813`)

| # | Check | Result |
|---|-------|--------|
| P1 | `GET /health` | `{"status":"ok"}` |
| P2 | `GET /health/ready` | `auth_required: false` |
| P3 | `GET /account` (no auth) | `signed_in: false`, `paid: false` |
| P4 | `POST /compare` (synthetic PDFs, no auth) | **200** ~14s |
| P5 | CORS preflight from `checkyourdrawings.kvshvl.in` | **200**, `Access-Control-Allow-Origin` matches |
| P6 | Frontend `https://checkyourdrawings.kvshvl.in` | **200** |
| P7 | `/about` | **200** |

**Manual still recommended:** upload real `0A`/`0B` smoke PDFs in browser, confirm overlay + PDF/PNG download, batch tab upsell for unsigned user.

**Note:** `scripts/smoke_pass3.py` authed compare expects `/outputs/` PNG + PDF paths on Render. Anonymous compare is the production freemium path.
