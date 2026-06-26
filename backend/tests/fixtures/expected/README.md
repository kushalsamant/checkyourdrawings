# Level3 overlay golden references

Visual sign-off PNGs for the committed level3 PDF pair (`level3_a.pdf` / `level3_b.pdf`).

| File | Purpose |
|------|---------|
| `level3_overlay.png` | Canonical golden at current pipeline settings (`OVERLAY_AGREE_DILATION_RADIUS=3`, hi-res B crop, close-only comparison masks) |
| `level3_overlay_dilation2.png` | A/B reference before dilation bump |
| `level3_overlay_dilation3.png` | A/B reference at dilation 3 |

Regenerate:

```powershell
python scripts/render_level3_dilation_ab.py
python scripts/render_level3_golden.py
```

Human review only — not wired to pytest SSIM yet.
