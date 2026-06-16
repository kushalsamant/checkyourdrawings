# Check Your Drawings

Check Your Drawings is a local MVP for comparing two drawing revisions. It accepts PDF, PNG, JPG, or JPEG files, aligns Revision B onto Revision A, detects visual changes, classifies regions as additions, deletions, or modifications, and renders a downloadable comparison image.

## Architecture

- React + TypeScript frontend in `frontend/`
- FastAPI backend in `backend/`
- OpenCV/NumPy computer vision pipeline in `backend/app/services/`
- Generated comparison images served from `http://127.0.0.1:8000/outputs/...`

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

All backend settings use the `CYD_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `CYD_MAX_FILE_SIZE_MB` | `100` | Maximum upload size per file |
| `CYD_PDF_DPI` | `300` | PDF rasterization DPI |
| `CYD_MAX_IMAGE_PIXELS` | `50000000` | Maximum decoded pixel count |
| `CYD_MAX_IMAGE_DIMENSION` | `12000` | Maximum image width or height |
| `CYD_OUTPUT_MAX_AGE_HOURS` | `24` | Delete old comparison PNGs after this many hours |
| `CYD_COMPARE_TIMEOUT_SECONDS` | `300` | Reserved for future server-side timeout enforcement |
| `CYD_CORS_ORIGINS` | localhost dev origins | Comma-separated allowed frontend origins |

## Frontend

```powershell
cd C:\Users\ADMIN\Documents\GitHub\checkyourdrawings\frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

The Vite dev server proxies `/compare`, `/outputs`, and `/health` to the backend.

### Production build

```powershell
cd frontend
$env:VITE_API_BASE_URL="https://api.example.com"
npm run build
```

Serve the contents of `frontend/dist/` from your static host and point `VITE_API_BASE_URL` at the deployed API.

## Testing

See [docs/testing.md](docs/testing.md).

Quick start:

```powershell
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
pytest backend/tests -v

cd frontend
npm test
```

## Pipeline

1. Upload Revision A and Revision B.
2. Convert PDF or image inputs into image arrays.
3. Align Revision B onto Revision A using ORB features and RANSAC homography.
4. Detect meaningful changed regions with thresholding, morphology, and contours.
5. Render a final comparison image with green additions, red deletions, and yellow modifications.
