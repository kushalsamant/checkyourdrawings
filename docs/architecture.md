# Architecture

Check Your Drawings is organized around the computer vision pipeline, not around SaaS features yet.

```text
React frontend
  -> POST /compare
FastAPI backend
  -> load PDF/image
  -> align Revision B to Revision A
  -> detect changed regions
  -> render annotated output
  -> serve generated PNG
```

The highest-risk product code lives in:

- `backend/app/services/alignment.py`
- `backend/app/services/differencer.py`
- `backend/app/services/renderer.py`

SaaS concerns such as authentication, billing, persistent project storage, teams, and background jobs should come after the comparison engine performs reliably on real drawings.
