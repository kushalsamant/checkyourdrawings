# High-Resolution B Re-warp Fix

## Summary

When the compare pipeline exported overlays at a higher DPI than the alignment raster (typically 300 DPI output from 200 DPI alignment), a broken **high-resolution Drawing B re-warp** path produced a gray, ink-saturated B crop. The coordination map classified ~97% of ink pixels as changed (mostly blue) even though alignment metrics looked healthy.

Commit `347d947` fixed this by **stopping the broken re-warp**, re-rasterizing Drawing A from the PDF clip at output DPI, and **upscaling the already-aligned low-resolution B crop** to match. It also added **crop-level ECC refinement** and **ink agreement tolerance** (mask dilation) so sub-pixel differences did not dominate the overlay.

---

## Background

The compare pipeline (`run_comparison_pipeline` in `backend/app/services/comparison_pipeline.py`) works in stages:

1. **Rasterize** page 1 of each PDF at an alignment DPI chosen by `choose_raster_dpi()` (capped by `COMPARE_MAX_RASTER_PIXELS`, often **200 DPI** for full architectural sheets).
2. **Align** Drawing B onto Drawing A with ORB features, RANSAC homography, and optional ECC (`align_drawing_b_to_a()`). ECC is skipped when the page exceeds `COMPARE_DISABLE_ECC_ABOVE_PIXELS` (3M pixels).
3. **Detect content** bounding boxes on A and aligned B; compute overlap and a union `comparison_bbox`.
4. **Choose output DPI** via `choose_output_dpi()` — can be higher than alignment DPI (up to `PDF_DPI` / 300) when the crop fits memory limits.
5. **Build comparison crops** at output resolution.
6. **Render** a coordination map (orange / blue / green / red ink) via independent ink masks on each crop.
7. **Export** PNG (with footer) and crop-layout PDF.

Commit `f6f287d` (2026-06-24) introduced high-resolution exports: when `output_dpi > alignment_dpi`, Drawing A was re-rasterized from the PDF clip at output DPI via `rasterize_pdf_bbox()`, while Drawing B was taken from the **already-aligned alignment-DPI image**, cropped, and resized with `cv2.INTER_CUBIC` to match A’s crop dimensions.

---

## Problem

On real MVP architectural PDF pairs (e.g. `level3_a.pdf` / `level3_b.pdf`), the coordination map showed:

- **~97% of ink pixels classified as changed** (`changed_pixel_ratio ≈ 0.97`), dominated by **blue** (only-in-B).
- Visually: a mostly blue/noisy sheet instead of green perimeter walls with selective orange/blue edits.
- **Alignment still reported `high` confidence** with inlier ratio ~0.94 — the failure was not caught by alignment gates or the existing absolute green-pixel floor in tests.

The symptom appeared when **`output_dpi` (300) > `alignment_dpi` (200)** — i.e. whenever the hi-res export path ran.

---

## Root Cause

The failure was a **resolution and coordinate-space mismatch** in the hi-res Drawing B path, not a bad homography.

### Broken implementation (investigation-era working tree)

During investigation, `_build_comparison_crops()` used a hi-res B re-warp roughly equivalent to:

1. Re-rasterize Drawing A from the PDF clip at `output_dpi` (correct).
2. Load Drawing B with `load_image_with_page_info(drawing_b_path, dpi=output_dpi)`.
3. Compute `scale = output_dpi / alignment_dpi` and `scaled_homography = scale_homography(homography, scale / b_scale)` where `b_scale = drawing_b_page.raster_dpi / alignment_dpi`.
4. Warp B onto a canvas of size `(drawing_a_image.shape × scale)` via `warp_drawing_with_homography()`.
5. Crop with `scale_bbox(comparison_bbox, scale)`.

**This variant is not present in the git parent of `347d947`** (`f6f287d` used upscale-only for B). It existed in the **working tree under investigation** before the fix was committed. **Unknown** who authored the intermediate re-warp or whether it was ever pushed to a remote branch.

### Why that breaks

For the level 3 MVP pair, investigation measured:

| Signal | Drawing A crop | Drawing B crop (broken path) |
|--------|----------------|----------------------------|
| Grayscale mean | ~251 | ~138 |
| Pixels &lt; 250 | ~3.5% | ~53% |
| Ink mask size (`build_foreground_mask`) | ~279k px | ~6.3M px |
| Mask overlap | ~165k px | — |

At **alignment DPI**, both crops were healthy (mean ~251, ~3.7% non-white). The corruption appeared **only after the hi-res B re-warp**.

Concrete mismatches:

1. **`load_image_with_page_info(..., dpi=300)` does not guarantee a 300 DPI raster.** `convert_pdf_page_to_image()` calls `choose_raster_dpi()` with `COMPARE_MAX_RASTER_PIXELS`. For a full page, the raster often stays at **200 DPI** even when 300 is requested.
2. **Canvas scaling assumed B was natively at `output_dpi`.** With `alignment_dpi = 200`, `b_page.raster_dpi = 200`, `output_dpi = 300`: `scale = 1.5`, `b_scale = 1`, so `scale_homography(H, 1.5)` was applied and B was warped to a canvas **1.5× the alignment-resolution page size**.
3. **Warping a 200 DPI image onto a 1.5× larger canvas** with `INTER_LINEAR` and white borders produced a gray, interpolation-heavy image. Adaptive ink detection treated most of the crop as foreground.
4. **Drawing A** came from a **PDF clip raster** at true 300 DPI (smaller region, fits pixel budget). **Drawing B** came from a **mis-scaled warp** of a lower-DPI full-page image. The two crops were not in the same effective coordinate or anti-aliasing space.
5. **Overlay classification** uses strict per-pixel mask overlap (`a_mask & b_mask` before tolerance). When B’s mask is ~22× larger than A’s with minimal overlap, almost all B ink becomes **blue**.

ECC at alignment DPI could not repair this — the damage occurred **after** alignment, in the hi-res crop builder.

---

## Investigation

### Tools and fixtures

- `scripts/diagnose_compare.py` — runs `run_comparison_pipeline`, prints metadata JSON (stdout only).
- `scripts/test_mvp_assets.py` — batch table over four MVP pairs in `backend/tests/fixtures/pdfs/`.
- `COMPARE_DEBUG=true` / `--debug` — writes frames to `backend/outputs/debug/<run-id>/` (`01`–`06`, including `04_drawing_a_crop`, `05_drawing_b_crop`, `06_overlay_map`).
- Canonical repro pair: **`level3_a.pdf` / `level3_b.pdf`** (same sources as `assets/3A` / `3B`).

### Observations (level 3, broken path)

Metadata from `diagnose_compare.py` before the fix:

```json
"overlay": {
  "orange_pixels": 109276,
  "blue_pixels": 5957768,
  "green_pixels": 165255,
  "red_pixels": 225127
},
"differences": { "changed_pixel_ratio": 0.974 },
"alignment_confidence": { "status": "high" },
"alignment": { "inlier_ratio": 0.938 }
```

Target crop shape at output DPI: **3779 × 3225** (scale 1.5 from alignment bbox).

### Hypotheses tested

| Hypothesis | Result |
|------------|--------|
| Bad homography / low inliers | **Rejected** — inlier ratio ~0.94, homography near identity on level 3 |
| Ink detection too aggressive (CLAHE + Otsu ∪ adaptive) | **Partial** — fatter masks amplify the problem but do not explain B mean 138 vs A mean 251 |
| Missing ECC on hi-res crops | **Partial** — crop ECC alone did not fix blue dominance while broken warp remained |
| Strict `agree = a_mask & b_mask` | **Partial** — agree dilation helped green count but blue stayed ~5.96M until warp was fixed |
| Hi-res B warp DPI / canvas mismatch | **Confirmed** — low-res crops healthy; hi-res B crop gray and 6.3M ink mask |

### Identification method

Isolated `_build_comparison_crops()` with a short Python diagnostic script:

- Compared grayscale statistics and mask sizes for A crop vs B crop.
- Compared **low-res** `crop_image(aligned_drawing_b, bbox)` vs **hi-res** warp path.
- Traced `b_page.raster_dpi` vs requested `output_dpi` and warp output dimensions.

The smoking gun: **B crop mean ~138 and b_mask ~6.3M only on the hi-res re-warp path**; upscale-from-aligned-low-res and direct `rasterize_pdf_bbox(B, same bbox)` both produced B stats matching A.

---

## Alternatives Considered

### 1. Crop-level ECC only (`refine_crop_alignment`)

**Tried.** Refines sub-pixel alignment on hi-res crops (with downscale when crops exceed `CROP_ECC_MAX_PIXELS`).

**Rejected as sole fix** — with the broken B warp, blue pixel count stayed ~5.96M. ECC cannot fix a crop whose grayscale distribution is fundamentally wrong.

**Kept in `347d947`** as a supplement after the warp fix.

### 2. Ink agreement tolerance (`OVERLAY_AGREE_DILATION_RADIUS`)

Dilate masks before computing `agree` so 1–3 px anti-aliasing offsets count as green.

**Tried.** With broken warp: green rose (~165k → ~318k), blue **unchanged** at ~5.96M.

**Kept in `347d947`** — necessary for real PDF linework after warp fix; not sufficient alone.

### 3. Upscale aligned low-res B crop (`cv2.INTER_CUBIC`)

Crop `aligned_drawing_b` at alignment DPI, resize to match A’s hi-res crop.

**Chosen in `347d947`.** Preserves alignment already computed at alignment DPI; avoids re-warp coordinate bugs. B crop stats match A (mean ~251, ink ~250k–470k depending on dilation).

**Trade-off:** B linework is interpolated from 200 DPI, not re-rendered from PDF at 300 DPI. Acceptable for MVP; identity-ish homographies on level 3.

### 4. Symmetric ink detection (shared threshold on A and B)

Apply one threshold or mask strategy to both grayscales.

**Considered, not needed** once crops were balanced. **Unknown** if still needed for large non-identity homographies.

### 5. Direct `rasterize_pdf_bbox(B, comparison_bbox)` at output DPI (no warp)

Works when homography ≈ identity (same sheet, same bbox in page space).

**Rejected for general case** — margin shifts and non-identity homographies require warping B in A’s coordinate space.

### 6. Full-page `rasterize_pdf_bbox(B)` + `scale_homography(H, scale)` + warp + crop

Rasterize B’s full page at output DPI from PDF (not `load_image_with_page_info`), warp with homography scaled by `output_dpi / alignment_dpi`, crop scaled bbox.

**Post-`347d947` working-tree implementation** (present in repo **after** `347d947`, **uncommitted** as of this document). Theoretically avoids the `load_image_with_page_info` DPI lie. **Unknown** whether this has been fully validated on all four MVP pairs or pushed.

### 7. Golden PNG / SSIM regression

**Deferred** — human sign-off against `assets/expected-comparison-result3.png` first.

---

## Final Solution

Commit **`347d947`** (`Fix compare overlay quality and add MVP PDF regression tests`).

### Hi-res crop builder (`_build_comparison_crops`)

When `output_dpi > alignment_dpi`:

1. **Drawing A** — `rasterize_pdf_bbox(drawing_a_path, comparison_bbox, source_dpi=alignment_dpi, target_dpi=output_dpi)`.
2. **Drawing B** — `crop_image(aligned_drawing_b, comparison_bbox)` at **alignment DPI**, then `cv2.resize(..., INTER_CUBIC)` to A crop dimensions (no hi-res re-warp).

When `output_dpi <= alignment_dpi`, both sides are cropped directly from alignment-resolution images (unchanged).

### Crop ECC (`refine_crop_alignment`)

After crops are built, run `refine_crop_alignment(drawing_a_crop, aligned_drawing_b_crop)` before overlay render. Downscales for `cv2.findTransformECC` when crop pixel count exceeds `CROP_ECC_MAX_PIXELS` (4M), then scales translation back to full resolution.

### Ink agreement tolerance

`OVERLAY_AGREE_DILATION_RADIUS` (default **2** in `347d947`; **3** in later uncommitted `config.py`) — dilate A and B masks before `agree = a_for_agree & b_for_agree`.

### Guardrails and tests

- `validate_overlay_stats()` — reject effectively blank overlays (`MIN_INK_PIXEL_RATIO`).
- Eight MVP PDF fixtures committed under `backend/tests/fixtures/pdfs/`.
- Ratio gates: `MIN_GREEN_RATIO = 0.25`, `MAX_CHANGED_RATIO = 0.60` in `test_mvp_asset_pdfs.py`.
- Debug frames via `compare_debug.py` when `COMPARE_DEBUG=true`.

---

## Why This Works

1. **Alignment is computed once** at alignment DPI where memory and ORB/ECC constraints are known-good.
2. **Upscaling an aligned bitmap** applies a uniform scale to both drawings’ crop regions — no mixed coordinate spaces between fitz clip raster and OpenCV warp canvas.
3. **A still gets true vector re-rasterization** at output DPI from the PDF, improving A-side sharpness without corrupting B.
4. **Crop ECC** recovers sub-pixel residual error introduced by upscaling B.
5. **Agree dilation** absorbs remaining 1–2 px anti-aliasing differences between fitz (A) and cubic upscale (B).

Once B crop grayscale stats match A, independent ink masks overlap on unchanged linework → **green** dominates; real edits remain orange/blue.

---

## Trade-offs

| Topic | Limitation |
|-------|------------|
| B sharpness at 300 DPI | B is upscaled from 200 DPI alignment crop, not PDF re-rendered at 300 DPI (unless post-347d947 warp path is adopted) |
| Large homographies | Upscale path assumes alignment at low DPI is good enough; extreme perspective may need a correct PDF re-warp, not upscale |
| ECC at alignment | Still disabled above 3M pixels on full page; crop ECC compensates only after cropping |
| Agree dilation | Radius 2–3 px can merge nearby distinct orange/blue pairs on very fine edits |
| Tests | Ratio gates catch gross regression; **no committed golden PNG SSIM** yet |
| Production | `347d947` was **ahead of origin** at time of writing — **Unknown** if deployed to Render |

---

## Testing

### Automated (commit `347d947`)

| Suite | Result |
|-------|--------|
| `pytest -q` from `backend/` | **101 passed** (includes MVP PDF test, compare accuracy, pipeline e2e) |
| `test_mvp_asset_pdfs.py` | All 4 levels: green ≥ 100k, green ratio ≥ 25%, changed ratio ≤ 60%, inlier ≥ 0.55, confidence `high`, DPI ≥ 200, mode `crop` |
| `scripts/test_mvp_assets.py` | All 4 levels pass (batch table) |

### Level 3 metrics after fix (reproducible via `diagnose_compare.py`)

| Metric | Before (broken warp) | After (`347d947`) |
|--------|----------------------|-------------------|
| `green_pixels` | 165,255 | 374,685 |
| `blue_pixels` | 5,957,768 | 294,636 |
| `changed_pixel_ratio` | 0.974 | 0.504 |
| Green % of ink | ~3% | ~49.6% |

Exact counts may shift slightly if `OVERLAY_AGREE_DILATION_RADIUS` changes (2 in `347d947`, 3 in uncommitted config).

### Manual verification remaining

- Side-by-side visual check vs `assets/expected-comparison-result3.png` (not wired to CI).
- **Unknown** — whether post-`347d947` uncommitted `rasterize_pdf_bbox` + warp path was regression-tested.

---

## Lessons Learned

1. **High alignment confidence does not imply good overlays** — validate crop-level image statistics and mask overlap, not just homography inliers.
2. **Never mix raster sources without proving identical DPI and coordinate spaces** — PDF clip raster vs `load_image` vs warp canvas are three different pipelines.
3. **`choose_raster_dpi()` silently caps DPI** — requesting `dpi=300` does not mean the image is 300 DPI.
4. **`scale_homography(H, scale)` only applies when source and target resolutions are consistent** with how `H` was estimated.
5. **Absolute pixel floors hide ratio failures** — `green_pixels >= 100_000` passed while ~97% of ink was false blue; ratio gates are necessary.
6. **Debug frames (`04`/`05` crops) are the fastest way to spot gray-B corruption** before tuning ink thresholds.

---

## Files Changed

### Commit `347d947` (primary)

| File | Purpose |
|------|---------|
| `backend/app/services/comparison_pipeline.py` | Hi-res A raster + B upscale; crop ECC hook; debug frames; blank validation |
| `backend/app/services/alignment.py` | `refine_crop_alignment()`, `scale_homography()`, ECC helper refactor |
| `backend/app/services/overlay_renderer.py` | Agree dilation; `validate_overlay_stats()` |
| `backend/app/services/image_utils.py` | CLAHE + Otsu ∪ adaptive ink masks (blank-output hardening) |
| `backend/app/config.py` | `overlay_agree_dilation_radius`, `crop_ecc_max_pixels`, `compare_max_raster_pixels` |
| `backend/app/services/compare_debug.py` | Optional intermediate PNG export |
| `backend/tests/test_mvp_asset_pdfs.py` | Four MVP pairs + ratio gates |
| `backend/tests/test_compare_accuracy.py` | `scale_homography`, crop ECC, agree tolerance unit tests |
| `backend/tests/fixtures/pdfs/*.pdf` | Committed architectural revision pairs |
| `scripts/diagnose_compare.py` | Single-pair diagnostic CLI |
| `scripts/test_mvp_assets.py` | Batch runner with green%/changed% columns |

### Related (not the warp fix itself)

| File | Purpose |
|------|---------|
| `backend/app/services/pdf_exporter.py` | Crop PDF layout (earlier quality work) |
| `f6f287d` — `comparison_pipeline.py` | Introduced hi-res A export + `choose_output_dpi` |

### Post-`347d947` (uncommitted at document time)

| File | Purpose |
|------|---------|
| `backend/app/services/comparison_pipeline.py` | Replaced B upscale with `rasterize_pdf_bbox` full-page + `scale_homography(H, scale)` warp — **status Unknown** |

---

## Related Commits

| Commit | Date | Summary |
|--------|------|---------|
| **`347d947`** | 2026-06-25 | **This fix** — B upscale instead of broken re-warp; crop ECC; agree dilation; MVP PDF tests |
| `f6f287d` | 2026-06-24 | Hi-res A PDF crop export; B crop + resize; crop PDF layout; `choose_output_dpi` |
| `b1fa241` | 2026-06-21 | Extracted `comparison_pipeline.py`; single-pair compare flow |

**Unknown:** SHAs of any unpushed branch containing the broken `load_image_with_page_info` re-warp variant.

---

## Document metadata

- **Authoring source:** Git history (`347d947`, `f6f287d`), source code, commit messages, and investigation diagnostics on `level3` MVP fixtures.
- **Not sourced from git:** Exact broken re-warp code path (reconstructed from investigation working tree; not in `347d947^`).
- **IDE note:** `backend/outputs/` is listed in `.cursorignore` — agents cannot read generated PNGs; use Explorer or `COMPARE_DEBUG` frames locally.
