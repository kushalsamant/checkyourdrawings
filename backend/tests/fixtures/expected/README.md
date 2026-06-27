# Level3 overlay golden references

Visual sign-off PNGs for the committed level3 PDF pair (`level3_a.pdf` / `level3_b.pdf`).

| File | Purpose |
|------|---------|
| `level3_overlay.png` | Canonical golden at current pipeline settings (`OVERLAY_AGREE_DILATION_RADIUS=3`, hi-res B crop, close-only comparison masks) |

CI regression: `backend/tests/test_level3_golden_overlay.py` — exact ink stats + ink pixel labels; small background tolerance for anti-aliasing.

Optional local A/B (gitignored):

| File | Purpose |
|------|---------|
| `level3_overlay_dilation2.png` | A/B reference before dilation bump |
| `level3_overlay_dilation3.png` | A/B reference at dilation 3 |

Regenerate after intentional pipeline changes:

```powershell
python scripts/render_level3_dilation_ab.py
python scripts/render_level3_golden.py
py -3.12 -m pytest backend/tests/test_level3_golden_overlay.py -q
```
