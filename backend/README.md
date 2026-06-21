# Backend API

FastAPI service for PDF drawing comparison and account status.

Repo overview: [../README.md](../README.md).

## Endpoints

- `GET /` — service info
- `GET /health` — upload/output directory health
- `GET /health/ready` — readiness probe
- `GET /account` — signed-in and paid status (optional auth via Bearer token)
- `POST /compare` — compare two PDF drawings (rate limited per IP)
- `GET /outputs/<file>` — generated comparison PNG/PDF (static; pruned after 24h)

All responses include basic security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Strict-Transport-Security`).

## Auth environment variables

Set in `.env` (see repo root `.env.example` for `CYD_*` settings):

- `PLATFORM_DATABASE_URL` — Postgres URL for user accounts (required when `CYD_AUTH_REQUIRED=true`)
- `PLATFORM_JWT_SECRET` — verifies tokens from KVSHVL auth
- `PLATFORM_JWT_ISSUER` — JWT issuer (default production: `https://auth.kvshvl.in`)

When `CYD_AUTH_REQUIRED=false`, compare works without sign-in; `/account` still accepts an optional token.

## Rate limiting

`POST /compare` is rate limited per client IP (in-memory, per process). Over the limit returns `429` with a `Retry-After` header. Configure via:

- `CYD_RATE_LIMIT_ENABLED` — default `true`
- `CYD_RATE_LIMIT_MAX_REQUESTS` — default `20`
- `CYD_RATE_LIMIT_WINDOW_SECONDS` — default `60`

## Compare request

Multipart form fields:

- `drawing_a` — PDF file (required)
- `drawing_b` — PDF file (required)

## Compare response

```json
{
  "image_path": "/outputs/comparison-<uuid>.png",
  "pdf_path": "/outputs/comparison-<uuid>.pdf",
  "metadata": {
    "alignment": {
      "keypoints_drawing_a": 0,
      "keypoints_drawing_b": 0,
      "raw_matches": 0,
      "good_matches": 0,
      "inlier_matches": 0,
      "inlier_ratio": 0.0,
      "homography": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
      "output_width": 0,
      "output_height": 0
    },
    "alignment_confidence": { "status": "high", "message": null },
    "content": {
      "drawing_a_bbox": { "x": 0, "y": 0, "width": 0, "height": 0 },
      "drawing_b_bbox": { "x": 0, "y": 0, "width": 0, "height": 0 },
      "overlap_bbox": { "x": 0, "y": 0, "width": 0, "height": 0 },
      "comparison_bbox": { "x": 0, "y": 0, "width": 0, "height": 0 }
    },
    "overlay": {
      "orange_pixels": 0,
      "blue_pixels": 0,
      "green_pixels": 0,
      "red_pixels": 0
    },
    "differences": {
      "width": 0,
      "height": 0,
      "changed_pixel_count": 0,
      "changed_pixel_ratio": 0.0
    },
    "output_page": {
      "mode": "source_a",
      "width_pt": 595.0,
      "height_pt": 842.0,
      "raster_dpi": 300
    }
  }
}
```

Only **`.pdf`** uploads are accepted (validated by extension and `%PDF-` magic bytes).

## Compare error codes

- `400` — empty file, non-PDF/corrupt upload, or drawings that cannot be aligned
- `413` — file exceeds the size limit
- `415` — unsupported file type
- `429` — rate limited (includes `Retry-After`)
- `503` — another comparison is already in progress
- `504` — comparison timed out

## Tests

```powershell
cd backend
..\.venv\Scripts\pytest
```
