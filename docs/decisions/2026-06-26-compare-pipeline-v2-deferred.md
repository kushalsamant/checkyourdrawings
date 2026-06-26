# Compare Pipeline v2 — Deferred

## Status

**Deferred.** MVP ships the raster pipeline in `comparison_pipeline.py`.

## Proposed architecture

```
render
  → deskew
  → homography
  → elastic refine
  → line extraction
  → adaptive diff
  → visualization
```

## Why it might be better

- Sub-pixel and local distortion handled by elastic refinement, not global dilation tolerance.
- Geometry-level diff is more stable than per-pixel ink masks when stroke weights differ.
- Thin linework and OCR-sized text compare as extracted lines, not thresholded pixels.

## Why not now

1. **Measured gaps on level3 are narrow** — ~2–3 px crop ECC residual and asymmetric ink masking, not a broken alignment model.
2. **Raster pipeline is tested and signed off** — MVP PDF fixtures, golden overlay, ratio gates, CI.
3. **Line extraction on PDFs is the hard part** — without true vector path parsing, extraction still runs on rasters and can drop geometry.
4. **Iterative ECC was tested and rejected** — extra passes overcorrect (green 67% → 42% at 3 passes).
5. **Ship blocker is deploy**, not compare algorithm.

## MVP pipeline (current)

1. Rasterize PDFs at alignment DPI (capped by pixel budget).
2. ORB + RANSAC homography + optional full-page ECC.
3. Hi-res crops: PDF clip for A; PDF re-rasterize + scaled homography warp for B.
4. Crop ECC (single pass).
5. **Close-only** ink masks for overlay (`build_comparison_mask`); framing uses `build_framing_mask`.
6. Coordination map with agree-dilation radius 3.

## When to revisit v2

- Customer PDFs still fail after mask + ECC polish.
- Need sub-mm tolerance on large sheets with scan skew or elastic distortion.
- Willing to invest in **PDF vector path ingest**, not raster skeletonization.
- Broad regression corpus beyond four MVP pairs.

## Related

- `docs/decisions/2026-06-26-hires-b-rewarp.md` — hi-res B warp fix and overlay quality work.
