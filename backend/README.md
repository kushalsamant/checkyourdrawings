# Backend API

## Endpoints

- `GET /` — service info
- `GET /health` — upload/output directory health
- `POST /compare` — compare two PDF drawings

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
      "inlier_ratio": 0.0
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
    }
  }
}
```

Only **`.pdf`** uploads are accepted.
