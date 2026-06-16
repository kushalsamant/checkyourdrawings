# Manual Smoke Test

Use this checklist when testing with real drawing files. Have **Revision A** (older) and **Revision B** (newer) ready.

## Before you start

### 1. Start the backend

```powershell
cd C:\Users\ADMIN\Documents\GitHub\checkyourdrawings
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --reload
```

### 2. Start the frontend (second terminal)

```powershell
cd C:\Users\ADMIN\Documents\GitHub\checkyourdrawings\frontend
npm run dev
```

### 3. Quick health check

```powershell
curl http://127.0.0.1:8000/health
```

Expected: `"status": "ok"` (or `"degraded"` with a clear issue message).

Open the app: **http://127.0.0.1:5173**

---

## Smoke tests

Record pass/fail and notes for each row.

| # | Test | Steps | Pass? | Notes |
|---|------|-------|-------|-------|
| 1 | **PDF vs PDF** | Upload two PDF revisions of the same drawing. Click **Compare drawings**. | | |
| 2 | **Result image** | Comparison image loads; green/red/yellow regions look reasonable. | | |
| 3 | **Metadata** | Detected regions, changed pixels, and alignment inliers show non-error values. | | |
| 4 | **Download** | Click **Download**; PNG saves and opens correctly. | | |
| 5 | **Stale result** | After a successful compare, change one upload; old image should disappear before comparing again. | | |
| 6 | **PNG vs PNG** | Repeat with two PNG exports of the same drawing pair. | | |
| 7 | **Mixed format** | PDF as Revision A, PNG as Revision B (or vice versa). | | |
| 8 | **Same file twice** | Upload the same file for A and B; expect near-zero changes. | | |
| 9 | **Invalid file** | Try a `.gif` or `.txt`; expect a clear error, no crash. | | |
| 10 | **Large file** | If you have a big sheet, confirm compare completes or returns a clear size/limit error. | | |
| 11 | **Unequal margins** | Export the same plan twice with different white borders. Expect near-zero false edge changes. | | |
| 12 | **Title block only changed** | Compare revisions where only the title block changed. Review whether plan regions look reasonable. | | |
| 13 | **Different view** | Compare two files that are not the same view. Expect HTTP 400 or a marginal-confidence warning. | | |
| 14 | **Metadata panel** | After a successful compare, confirm overlap area and alignment confidence appear in metadata. | | |

---

## What to look for

**Good signs**
- Alignment completes without a homography error.
- Changed regions match what you expect on the sheet.
- Download works from the result viewer.
- Unequal white margins do not create large false-positive bands at page edges.
- Metadata shows overlap area and alignment confidence status.

**Red flags** (tell the agent when you report back)
- `Homography is unreliable` or alignment errors on normal drawings.
- `Alignment confidence is too low` on revisions that should match.
- Many false regions on unchanged areas, especially at page edges.
- Missing obvious changes you can see by eye.
- Download fails or image does not load.
- App hangs on **Comparing...** for more than a few minutes.

---

## Optional: API-only test

If the UI is fine but you want to test the API directly:

```powershell
curl -X POST http://127.0.0.1:8000/compare `
  -F "revision_a=@C:\path\to\revision-a.pdf" `
  -F "revision_b=@C:\path\to\revision-b.pdf"
```

Expected: JSON with `image_path` and `metadata`. Open `http://127.0.0.1:8000` + `image_path` in a browser.

---

## Report back

When you have results, share:

1. Which rows passed/failed.
2. File types and approximate sheet size (e.g. A1 PDF, 24×36).
3. Screenshots or a short description of bad regions, if any.
4. Any error messages from the UI or browser console (F12 → Console).
