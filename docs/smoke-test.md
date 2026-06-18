# Smoke test checklist

Manual sign-off for Pass 1. Use architectural PDF pairs plotted from CAD.

## Prerequisites

```powershell
# Terminal 1 — API
cd C:\Users\ADMIN\Documents\GitHub\checkyourdrawings
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --reload

# Terminal 2 — UI
cd frontend
npm run dev
```

Open **http://127.0.0.1:5173**

## Required smoke pair

| File | Role |
|------|------|
| `0A 02-Saurabh mishraR2-Model.pdf` | Drawing A |
| `0B 02-Saurabh mishraR2-Model.pdf` | Drawing B |

## Checklist

| # | Step | Expected | Pass |
|---|------|----------|------|
| 1 | Upload `0A` as Drawing A, `0B` as Drawing B | Both accepted (PDF only) | |
| 2 | Click **Compare** | Completes in under ~30s | |
| 3 | Result image | Visible **red** and **blue** at real drawing changes; green where ink matches | |
| 4 | Footer | Drawing A/B filenames, timestamp, color legend | |
| 5 | Metadata | Red/blue/green/magenta counts > 0 where expected; alignment confidence `high` or `marginal` | |
| 6 | **Download** | PNG saves and opens | |
| 7 | **Same file trap** | Upload same PDF twice → mostly **green** (correct for identical inputs) | |
| 8 | **Invalid file** | Try `.png` or `.dwg` → clear client-side or 415 error | |

## Overlay semantics

- **Red** = ink only in A  
- **Blue** = ink only in B  
- **Green** = ink in both (aligned)  
- **Magenta** = clash  

## API curl (optional)

```powershell
curl -X POST http://127.0.0.1:8000/compare `
  -F "drawing_a=@C:\path\to\drawing-a.pdf" `
  -F "drawing_b=@C:\path\to\drawing-b.pdf"
```

## Common mistakes

- Opening `:8000` in the browser — that is JSON API only; use `:5173`.
- Comparing **same file twice** and expecting red/blue — all green is correct.
- Comparing unrelated PDFs — alignment fails with HTTP 400 (by design).
