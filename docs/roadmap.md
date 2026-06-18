# Roadmap

## Pass 1 — Shipped

PDF-only coordination overlay tool for Drawing A vs Drawing B.

- Upload two PDFs → ORB/RANSAC align → orange/blue/green/red overlay PNG
- React UI + FastAPI backend; local `backend/outputs/` storage
- Smoke-signed-off on `0A`/`0B` architectural PDF pair (repo root, gitignored)

See [architecture.md](architecture.md), [smoke-test.md](smoke-test.md), and [testing.md](testing.md).

## Pass 2 — Production MVP (next)

Hosted, billable version of Pass 1 — same compare pipeline, production infrastructure.

- Supabase Auth + JWT-protected `POST /compare`
- Shared kvshvl platform Razorpay billing + per-user compare quota
- Comparison PNGs in Supabase Storage (`cyd_outputs`); metadata in Postgres
- Production Dockerfile; deploy API (Render/Fly) + UI (Vercel)
- Local dev still works with auth/storage bypass flags

## Pass 3 — Growth (later)

- Region detection in API metadata
- Team features, analytics
- Additional input formats (DWG, raster) if needed
