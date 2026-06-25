# MVP revision PDF fixtures

Committed copies of the local `assets/` revision set used for end-to-end compare tests.

| Drawing A | Drawing B | Source |
|-----------|-----------|--------|
| `level0_a.pdf` | `level0_b.pdf` | `0A` / `0B 02-Saurabh mishraR2-Model.pdf` |
| `level1_a.pdf` | `level1_b.pdf` | `1A` / `1B 02-Saurabh mishraR2-Model.pdf` |
| `level2_a.pdf` | `level2_b.pdf` | `2A` / `2B 02-Saurabh mishraR2-Model.pdf` |
| `level3_a.pdf` | `level3_b.pdf` | `3A` / `3B 02-Saurabh mishraR2-Model.pdf` |

Drawing A is the earlier revision; Drawing B is the later revision for each level.

Tests: `backend/tests/test_mvp_asset_pdfs.py`  
Batch runner: `python scripts/test_mvp_assets.py`
