# Backend API

## Endpoints

- `GET /` — service info
- `GET /health` — upload/output directory health
- `POST /compare` — compare two PDF drawings

## Compare request

Multipart form fields:

- `drawing_a` — PDF file (required)
- `drawing_b` — PDF file (required)

Aliases `revision_a` / `revision_b` are also accepted for backward compatibility.

## Compare response

```json
{
  "image_path": "/outputs/comparison-<uuid>.png",
  "metadata": {
    "alignment": { ... },
    "alignment_confidence": { "status": "high", "message": null },
    "content": {
      "reference_bbox": { ... },
      "revision_bbox": { ... },
      "overlap_bbox": { ... }
    },
    "overlay": {
      "red_pixels": 0,
      "blue_pixels": 0,
      "green_pixels": 0,
      "magenta_pixels": 0
    },
    "differences": {
      "width": 0,
      "height": 0,
      "regions": [],
      "changed_pixel_count": 0,
      "changed_pixel_ratio": 0.0
    }
  }
}
```

Only **`.pdf`** uploads are accepted.
