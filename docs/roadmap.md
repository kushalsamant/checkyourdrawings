# Roadmap

Full task list, architecture, and todos: [.cursor/plans/checkyourdrawings.plan.md](../.cursor/plans/checkyourdrawings.plan.md).

## Pass 1 — Shipped

PDF-only coordination overlay tool for Drawing A vs Drawing B.

- Upload two PDFs → ORB/RANSAC align → orange/blue/green/red overlay PNG
- React UI + FastAPI backend; local `backend/outputs/` storage
- Server-side compare timeout; smoke-signed-off on `0A`/`0B` pair (repo root, gitignored)

See [architecture.md](architecture.md), [smoke-test.md](smoke-test.md), and [testing.md](testing.md).

## Pass 2 — Production MVP (next)

Hosted version of Pass 1 — **same compare pipeline**, production infrastructure.

- Supabase Auth + JWT-protected `POST /compare`
- **kvshvl platform billing** — users subscribe on kvshvl.in; CYD reads subscription from shared `users` table (no CYD payments router)
- Comparison PNGs in Supabase Storage (`cyd_outputs`); metadata in `comparisons` table
- Production Dockerfile; deploy API (Render/Fly) + UI (Vercel at `checkyourdrawings.kvshvl.in`)
- Local dev: `CYD_AUTH_REQUIRED` and `CYD_STORAGE_BYPASS` flags
- Sketch2BIM repo = **reference patterns only** (~400–600 lines), not a full port

kvshvl.in side-tab CTA to Check Your Drawings: shipped in [kushalsamant.github.io](https://github.com/kushalsamant/kushalsamant.github.io).

## Pass 3 — Growth (later)

- Region detection in API metadata
- Team features, analytics
- Additional input formats (DWG, raster) if needed
