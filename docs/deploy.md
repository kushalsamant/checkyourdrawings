# Deploy checklist

Canonical deploy guide for **Check Your Drawings**.

| Surface | Value |
|---------|-------|
| Vercel project | `kvshvl/checkyourdrawings` |
| Frontend URL | https://checkyourdrawings.kvshvl.in |
| API URL (live) | https://checkyourdrawings.onrender.com |
| API custom domain | `api.checkyourdrawings.kvshvl.in` — **optional, DNS not configured** |

## 1. Render (API)

Blueprint: [`render.yaml`](../render.yaml)

**Freemium production env (required):**

| Key | Value |
|-----|-------|
| `CYD_AUTH_REQUIRED` | `false` |
| `CYD_CORS_ORIGINS` | `https://checkyourdrawings.kvshvl.in,https://www.checkyourdrawings.kvshvl.in` |

Outputs are served from Render disk at `/outputs/` (PNG preview + PDF deliverable). Users download to keep copies; Supabase is auth + batch billing only.

Apply env from local secrets (if configured). For freemium, `CYD_AUTH_REQUIRED` must be `false` in `.env.pass3.local` before running:

```powershell
.\.venv\Scripts\python.exe scripts\deploy_pass3_env.py
```

Or set keys manually in Render → **checkyourdrawings-api** → **Environment**.

Validate blueprint:

```powershell
render blueprints validate ./render.yaml
```

## 2. Vercel (frontend)

**Build config:** root [`vercel.json`](../vercel.json) runs `npm ci --prefix frontend` and builds `frontend/dist`.

`AboutPage` imports root [`index.md`](../index.md), so git-connected deploys must include the full repo. CLI deploy from repo root:

```powershell
cd C:\Users\ADMIN\Documents\GitHub\checkyourdrawings
vercel --prod --yes
```

**Environment variables:**

| Key | Example |
|-----|---------|
| `VITE_API_BASE_URL` | `https://checkyourdrawings.onrender.com` |
| `VITE_SUPABASE_URL` | `https://ytcnzhapqainbtkoshvh.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | (from Supabase dashboard) |
| `VITE_KVSHVL_UPGRADE_URL` | `https://kvshvl.in` |

## 3. Product tiers (implemented)

| Tier | Access |
|------|--------|
| Anonymous | Unlimited single-pair `/compare` + PNG download |
| Signed in, not paid | Same as anonymous |
| Paid kvshvl (`weekly`/`monthly`/`yearly`) | Batch UI + ZIP export |

## 4. Manual tasks (not in repo)

See **[manual-ops.md](manual-ops.md)** for step-by-step checklists:

- **Google OAuth consent screen** — App name `KVSHVL`, logo, homepage `https://kvshvl.in`
- **Friend share** — outreach template and feedback tracker
- **API custom domain (optional)** — CNAME `api.checkyourdrawings.kvshvl.in` → Render

### Unified kvshvl.in sign-in (deferred)

**Status:** Not implemented. CYD uses per-app Supabase OAuth (`ytcnzhap`) today.

**Target (requires kvshvl.in repo):**

1. CYD **Sign in** redirects to `https://kvshvl.in/sign-in?return_to=...`
2. kvshvl completes Google OAuth once (callback `https://kvshvl.in/api/auth/callback/google`)
3. Return to CYD with a platform JWT CYD already validates (`backend/app/auth/jwt.py`)
4. Remove CYD frontend `signInWithOAuth` via per-app Supabase

**Interim:** Google OAuth consent branding (manual-ops.md §1) reduces gibberish hostname concern.

### Optional infrastructure

| Item | Status |
|------|--------|
| `api.checkyourdrawings.kvshvl.in` DNS | Not live — `checkyourdrawings.onrender.com` is canonical |
| kvshvl.in portfolio link | **Live** — side tab in `kushalsamant.github.io/_includes/side-tabs.html` |

## 5. Smoke test

Follow [smoke-test.md](smoke-test.md).

Quick checks:

```powershell
curl.exe https://checkyourdrawings.onrender.com/health
curl.exe https://checkyourdrawings.kvshvl.in
```

Anonymous compare should return **200** without `Authorization`. Paid batch tab unlocks after `/account` reports `paid: true`.
