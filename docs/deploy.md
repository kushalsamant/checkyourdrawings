# Deploy checklist

Pass 2 deploy artifacts are in the repo. Finish hosting in the Render and Vercel dashboards.

## 1. Render (API)

1. Push this repo to GitHub.
2. [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint** → connect `checkyourdrawings` repo.
3. Render reads [`render.yaml`](../render.yaml) and creates `checkyourdrawings-api`.
4. Confirm env vars (set automatically from blueprint):
   - `CYD_AUTH_REQUIRED=false`
   - `CYD_STORAGE_BYPASS=true`
   - `CYD_CORS_ORIGINS=https://checkyourdrawings.kvshvl.in,https://www.checkyourdrawings.kvshvl.in`
5. After deploy, note the API URL (e.g. `https://checkyourdrawings-api.onrender.com`).
6. Optional: add custom domain `api.checkyourdrawings.kvshvl.in` in Render → service → **Settings** → **Custom Domains**.

Validate blueprint locally:

```powershell
render workspace set tea-d0c3aph5pdvs73d7acc0 --confirm
render blueprints validate ./render.yaml
```

## 2. Vercel (frontend)

Project created: **kvshvl/frontend** (root directory: `frontend/`).

1. Vercel → **kvshvl/frontend** → **Settings** → **Environment Variables**:
   - `VITE_API_BASE_URL` = your Render API URL (step 1 above)
2. **Redeploy** after setting the env var.
3. **Settings** → **Domains** → add `checkyourdrawings.kvshvl.in`.
4. DNS: CNAME `checkyourdrawings.kvshvl.in` → Vercel.

CLI deploy from `frontend/`:

```powershell
cd frontend
vercel --prod
```

## 3. Smoke test

Follow the **Hosted smoke test** section in [smoke-test.md](smoke-test.md).

## 4. kvshvl.in side tab

Already links to `https://checkyourdrawings.kvshvl.in` — no change needed once DNS is live.
