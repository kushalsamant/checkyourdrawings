# Backend API

FastAPI service for PDF drawing comparison via async jobs.

Repo overview: [../README.md](../README.md).

## Endpoints

- `GET /` — service info
- `GET /health` — upload/output directory health
- `GET /health/ready` — Postgres readiness when auth enabled
- `GET /allowance` — anonymous or signed-in allowance status
- `POST /compare` — enqueue comparison job (`202 { job_id }`)
- `GET /jobs/{job_id}` — poll job status and result (owner-only; 403 on mismatch)
- `GET /outputs/<file>` — legacy static outputs when Bunny is disabled

Account and billing live on **platform-api** (`/account`, `/payments/*`).

## Environment variables

- `PLATFORM_DATABASE_URL` — shared platform Postgres (job queue + readiness)
- `PLATFORM_API_URL` — entitlements and account proxy target
- `PLATFORM_JWT_SECRET` / `PLATFORM_JWT_ISSUER` — KVSHVL auth tokens
- `BUNNY_*` — storage zone, CDN hostname, token auth key (see [env.example](../env.example))

When `AUTH_REQUIRED=false`, anonymous users get a lifetime allowance of successful comparisons (`ANONYMOUS_ALLOWANCE_TOTAL`, default 5). Send `X-Anon-Session` (UUID v4) on compare and job poll requests. After the allowance is used, the next compare attempt returns `401` and requires Google sign-in.

## Rate limiting

`POST /compare` is rate limited per client IP. Configure via `RATE_LIMIT_*` env vars.

## Compare flow

1. Client `POST /compare` with `drawing_a` and `drawing_b` PDFs.
2. API returns `202` with `job_id`.
3. In-container worker processes jobs (`FOR UPDATE SKIP LOCKED`); paid users get higher priority.
4. Client polls `GET /jobs/{job_id}` until `status=completed`.
5. Result includes Bunny signed URLs for PNG/PDF when configured.

## Local run

```powershell
$env:PYTHONPATH = (Get-Location).Path
$env:PLATFORM_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/checkyourdrawings"
python scripts\migrate.py
uvicorn backend.app.main:app --reload --port 8000
```

## Deploy

Docker on Render; migrations run via `scripts/migrate.py` on container start.
