# Render ops — Check Your Drawings API

Operational notes for the app backend on Render. Reusable pattern for future KVSHVL apps: see [KVSHVL_APP_TEMPLATE.md](KVSHVL_APP_TEMPLATE.md).

## Live production

| Field | Value |
|-------|-------|
| Render service name | `checkyourdrawings-api` |
| Service ID | `srv-d8viasj7uimc738g0h0g` |
| Default URL | `https://checkyourdrawings-api.onrender.com` |
| Health check | `/health/ready` |
| Repo branch | `main` |
| Region / runtime | Ohio · Docker (`./Dockerfile`) |
| Frontend (Vercel) | `https://checkyourdrawings.kvshvl.in` |
| Vercel env | `VITE_API_BASE_URL=https://checkyourdrawings-api.onrender.com` |

## Naming (three layers)

| Layer | Check Your Drawings | Notes |
|-------|---------------------|-------|
| Repo / product slug | `checkyourdrawings` | Entitlements, Bunny prefix, GitHub repo |
| Render web service | `checkyourdrawings-api` | Dashboard name and CLI `--name` |
| `*.onrender.com` subdomain | `checkyourdrawings-api.onrender.com` | Set at **service creation**; rename does not change it |

**Rule:** `-api` suffix is for Render backends only. Entitlement slug, Bunny prefix, and repo name stay the bare app slug.

## Why we recreated the service (2026-06-27)

The original service was created as `checkyourdrawings`. Render assigned subdomain slug `checkyourdrawings` → `checkyourdrawings.onrender.com`.

Later the dashboard display name was renamed to `checkyourdrawings-api`, but **Render does not update `*.onrender.com` when you rename a service**. To get a matching subdomain, we:

1. Deleted old service `srv-d8qmgpr7uimc73e5bp9g`
2. Created a new service named `checkyourdrawings-api` at create time
3. Synced env, deployed, updated Vercel `VITE_API_BASE_URL`, redeployed frontend

Brief API downtime during cutover was expected.

**Alternative (no recreate):** add custom domain `checkyourdrawings-api.kvshvl.in` on the existing service (Coherence pattern). That does not change the default onrender.com hostname.

## Deploy env

Source of truth for `scripts/deploy_render_env.py` (merged in order):

1. Built-in defaults in the script (CORS, job limits, Bunny non-secrets)
2. `../platform-api/.env.deploy.local` — `PLATFORM_JWT_*`, `PLATFORM_DATABASE_URL`
3. `.env.bunnynet` — storage zone name/password (mapped to `BUNNY_STORAGE_*`)
4. `.env.deploy.local` — app overrides (optional; legacy `CYD_*` keys are mapped if present)
5. `../bunny-live-key.csv` — `BUNNY_TOKEN_AUTH_KEY` (pull zone token auth; never commit)

```powershell
cd checkyourdrawings
py -3.12 scripts/deploy_render_env.py
render deploys create srv-d8viasj7uimc738g0h0g --wait --confirm
```

## Bunny token auth key

Signed CDN URLs need `BUNNY_TOKEN_AUTH_KEY` (pull zone **Zone Security Key** when token authentication is enabled).

- **Pull zone:** `kvshvl-platform-cdn` (ID `6044716`) · hostname `kvshvl-platform-cdn.b-cdn.net`
- **Local export:** `../bunny-live-key.csv` (workspace root, gitignored)
- **Fetch via CLI:** `bunny api GET /pullzone` → `ZoneSecurityKey` on the matching zone

```powershell
bunny api GET /pullzone --output json
```

## Vercel frontend cutover

When the API origin changes:

```powershell
cd frontend
vercel env rm VITE_API_BASE_URL production --yes
"https://checkyourdrawings-api.onrender.com" | vercel env add VITE_API_BASE_URL production
vercel --prod
```

## Smoke test

```powershell
py -3.12 scripts/smoke_production.py
```

Set `SMOKE_INCLUDE_MVP_PDF=1` to run full MVP PDF pairs (may OOM on Render Free).

## Related scripts and files

| Path | Role |
|------|------|
| [render.yaml](../render.yaml) | Reference Blueprint (CLI provision, not Blueprint sync) |
| [scripts/deploy_render_env.py](../scripts/deploy_render_env.py) | Push env to Render |
| [scripts/smoke_production.py](../scripts/smoke_production.py) | Production health + compare smoke |
| [platform-api/scripts/sync_jwt_from_checkyourdrawings.py](https://github.com/kushalsamant/platform-api/blob/main/scripts/sync_jwt_from_checkyourdrawings.py) | Copy JWT vars from app Render → platform-api Render |

## What does not change with Render service ID

- Entitlement slug: `checkyourdrawings`
- Bunny prefix: `checkyourdrawings/`
- `CORS_ORIGINS` (frontend origins, not API URL)
- Postgres job data (shared `kvshvl-platform-db`)
