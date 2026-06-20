# Architecture

Check Your Drawings compares two **PDF** architectural drawings (Drawing A and Drawing B) and produces a **coordination overlay** as PNG (preview) and PDF (deliverable).

## Stack

```text
User laptop → upload → Render (compare, writes outputs/) → preview/download → user laptop
Vercel = UI only | Supabase = auth + batch billing | No output cloud storage
```

## Components

| Layer | Role |
|-------|------|
| `frontend/` | Upload UI, result viewer, metadata panel |
| `backend/app/routes/compare.py` | `POST /compare` — validate uploads, run pipeline |
| `backend/app/services/pdf_converter.py` | PyMuPDF rasterize PDF → RGB image |
| `backend/app/services/pdf_exporter.py` | Embed overlay PNG on Drawing A sheet PDF |
| `backend/app/services/alignment.py` | ORB features + RANSAC homography + optional ECC refinement |
| `backend/app/services/content_detection.py` | Ink bounding boxes, union crop, overlap gate |
| `backend/app/services/overlay_renderer.py` | Orange/blue/green/red ink map + footer band |
| `backend/outputs/` | Generated comparison PNG + PDF (served at `/outputs/`, pruned after 24h) |

## Request flow

```text
Drawing A PDF + Drawing B PDF
  → load_image (PyMuPDF)
  → align_drawing_b_to_a (ORB + RANSAC + optional ECC)
  → detect_content_bbox + union_bbox + compute_overlap_bbox (gate)
  → render_coordination_overlay (orange / blue / green / red)
  → comparison-{uuid}.png + comparison-{uuid}.pdf
```

## Alignment behavior

- **Hard fail (HTTP 400):** cannot compute homography, or insufficient overlapping ink between sheets.
- **Marginal (HTTP 200 + warning):** low inlier ratio — overlay still returned; footer notes low confidence.
- **Timeout (HTTP 504):** compare exceeds `CYD_COMPARE_TIMEOUT_SECONDS` (default 300s).

## Out of scope

- DWG, PNG, JPG, GIF inputs
- Comparison history / Supabase output storage — users download deliverables to their own systems

## Highest-risk code

- `backend/app/services/alignment.py` — homography quality drives usefulness
- `backend/app/services/overlay_renderer.py` — pixel classification semantics
- `backend/app/services/content_detection.py` — overlap gate rejects unrelated sheets
