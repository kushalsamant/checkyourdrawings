# Check Your Drawings

Check Your Drawings is an AEC coordination tool for comparing two architectural drawing PDFs. Upload Drawing A and Drawing B (plotted or exported from your design software), auto-align them, and download a coordination overlay PNG.

## Overlay semantics

The coordination overlay paints every ink pixel:

| Color | Meaning |
|-------|---------|
| Orange | Ink only in Drawing A |
| Blue | Ink only in Drawing B |
| Green | Ink in both (aligned overlap) |
| Red | Misaligned overlap (clash) |

**Same file twice → mostly green.** That is correct behavior for identical inputs.

## Repository layout

| Path | Purpose |
|------|---------|
| `backend/` | FastAPI app, compare pipeline, tests |
| `frontend/` | React UI |
| `docs/` | Architecture, roadmap, testing, smoke-test docs |
| `supabase/` | Supabase CLI scaffold (Pass 2 — auth, storage, billing) |
| Root config | `README.md`, `LICENSE`, `Dockerfile`, `.gitignore`, `.env.example` |

**Local-only at repo root (gitignored, do not commit):**

- Smoke PDFs: `0A`/`0B` (required) and optional `1A`–`3B` pairs for manual testing
- `.env` with your `CYD_*` settings

**Do not add at root:** DWG files, raster images, debug logs, or comparison output PNGs.

## Architecture

- React + TypeScript frontend in `frontend/`
- FastAPI backend in `backend/`
- Pipeline: PDF rasterize → ORB/RANSAC align → content crop → coordination overlay PNG
- Output served from `/outputs/...` (proxied in dev via Vite)

See [docs/roadmap.md](docs/roadmap.md) for Pass 1/2/3 scope. Full task list and todos: [.cursor/plans/checkyourdrawings.plan.md](.cursor/plans/checkyourdrawings.plan.md).

## Backend

```powershell
cd C:\Users\ADMIN\Documents\GitHub\checkyourdrawings
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Health check:

```powershell
curl http://127.0.0.1:8000/health
```

### Environment variables

All backend settings use the `CYD_` prefix (see [`.env.example`](.env.example)):

| Variable | Default | Description |
|----------|---------|-------------|
| `CYD_MAX_FILE_SIZE_MB` | `100` | Maximum upload size per file |
| `CYD_PDF_DPI` | `300` | PDF rasterization DPI |
| `CYD_MAX_IMAGE_PIXELS` | `50000000` | Maximum decoded pixel count |
| `CYD_MAX_IMAGE_DIMENSION` | `12000` | Maximum image width or height |
| `CYD_OUTPUT_MAX_AGE_HOURS` | `24` | Delete old comparison PNGs after this many hours |
| `CYD_COMPARE_TIMEOUT_SECONDS` | `300` | Server-side compare timeout (matches frontend 5 min) |
| `CYD_CONTENT_BBOX_PADDING_RATIO` | `0.02` | Padding around detected ink bounding boxes |
| `CYD_MIN_OVERLAP_AREA_RATIO` | `0.05` | Minimum shared ink overlap before comparing |
| `CYD_ALIGNMENT_MARGINAL_INLIER_RATIO` | `0.55` | Below this inlier ratio, API warns but still returns overlay |
| `CYD_ALIGNMENT_ECC_REFINEMENT` | `true` | Sub-pixel ECC pass after homography |
| `CYD_CORS_ORIGINS` | localhost dev origins | Comma-separated allowed frontend origins |

## Frontend

```powershell
cd C:\Users\ADMIN\Documents\GitHub\checkyourdrawings\frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173** (not `:8000`, which is API-only).

In local dev, leave `VITE_API_BASE_URL` unset so Vite proxies `/compare` and `/outputs` to the backend (see [`frontend/.env.example`](frontend/.env.example)).

### Production build

```powershell
cd frontend
$env:VITE_API_BASE_URL="https://api.example.com"
npm run build
```

## PDF workflow

In your design software, **plot or export a PDF** for each sheet revision, then upload Drawing A and Drawing B here.

Only **`.pdf`** uploads are accepted.

## Testing

See [docs/testing.md](docs/testing.md) and [docs/smoke-test.md](docs/smoke-test.md).

```powershell
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
pytest backend/tests -v

cd frontend
npm test
```

## Pipeline

1. Upload Drawing A and Drawing B (PDF).
2. Rasterize first page of each PDF at 300 DPI.
3. Align Drawing B onto Drawing A (ORB + RANSAC homography).
4. Crop to drawing content; classify pixels (orange/blue/green/red).
5. Render coordination overlay PNG with footer (filenames, timestamp, legend).
