# Architecture

Check Your Drawings compares two **PDF** architectural drawings and produces a **coordination overlay** PNG.

## Components

| Layer | Role |
|-------|------|
| `frontend/` | Upload UI, result viewer, metadata panel |
| `backend/app/routes/compare.py` | `POST /compare` — validate uploads, run pipeline |
| `backend/app/services/pdf_converter.py` | PyMuPDF rasterize PDF → RGB image |
| `backend/app/services/alignment.py` | ORB features + RANSAC homography |
| `backend/app/services/content_detection.py` | Ink bounding boxes, overlap gate, crop |
| `backend/app/services/overlay_renderer.py` | Diff-only pixel overlay + footer band |
| `backend/outputs/` | Generated comparison PNGs (served at `/outputs/`) |

## Request flow

```text
Drawing A PDF + Drawing B PDF
  → load_image (PyMuPDF)
  → align_revision_to_reference
  → detect_content_bbox + compute_overlap_bbox (gate)
  → render_coordination_overlay
  → comparison-{uuid}.png
```

## Alignment behavior

- **Hard fail (HTTP 400):** cannot compute homography, or insufficient overlapping ink between sheets.
- **Marginal (HTTP 200 + warning):** low inlier ratio — overlay still returned; footer notes low confidence.

## Out of scope (v1)

- DWG, PNG, JPG, GIF inputs
- Region boxes in API metadata (`differences.regions` is always empty)
- Auth, billing, cloud storage (Pass 2 / Supabase)

## Highest-risk code

- `backend/app/services/alignment.py` — homography quality drives usefulness
- `backend/app/services/overlay_renderer.py` — pixel classification semantics
- `backend/app/services/content_detection.py` — overlap gate rejects unrelated sheets
