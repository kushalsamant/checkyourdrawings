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
| `CYD_STORAGE_BYPASS` | `true` |
| `CYD_CORS_ORIGINS` | `https://checkyourdrawings.kvshvl.in,https://www.checkyourdrawings.kvshvl.in` |

Paid cloud storage (`CYD_STORAGE_BYPASS=false`) is only needed when persisting comparisons for subscribed users.

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
| Anonymous | Unlimited single-pair `/compare`, watermarked PNG |
| Signed in, not paid | Same as anonymous |
| Paid kvshvl (`weekly`/`monthly`/`yearly`) | Batch UI + unwatermarked PNGs + ZIP export |

## 4. Manual tasks (not in repo)

- **Google OAuth consent screen:** App name `KVSHVL`, logo, homepage `https://kvshvl.in`
- **Unified kvshvl.in sign-in:** requires kvshvl.in app changes to return platform JWT to child apps (Check Your Drawings still uses Supabase OAuth until then)
- **Friend share:** send https://checkyourdrawings.kvshvl.in to coordination contacts for feedback
- **API custom domain (optional):** CNAME `api.checkyourdrawings.kvshvl.in` → Render

## 5. Smoke test

Follow [smoke-test.md](smoke-test.md).

Quick checks:

```powershell
curl.exe https://checkyourdrawings.onrender.com/health
curl.exe https://checkyourdrawings.kvshvl.in
```

Anonymous compare should return **200** without `Authorization`. Paid batch tab unlocks after `/account` reports `paid: true`.
