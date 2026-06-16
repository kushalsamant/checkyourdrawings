# Testing

Check Your Drawings uses a combinatorial automated test matrix plus a short manual smoke checklist.

## Backend

From the repository root with the virtual environment activated:

```powershell
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
pytest backend/tests -v
```

Skip slower tests:

```powershell
pytest backend/tests -v -m "not slow"
```

### Matrix coverage

| Layer | What is covered |
|-------|-----------------|
| File type pairs | All 16 combinations of `.pdf`, `.png`, `.jpg`, `.jpeg` for Revision A × Revision B |
| Content scenarios | identical, addition, deletion, modification, mixed, same-file |
| Pipeline units | alignment, differencer, renderer, file validation, image limits, output cleanup |
| API errors | empty upload, unsupported type, corrupt image, oversize bytes, response shape |

Synthetic fixtures are generated in tests via Pillow and PyMuPDF. No large binary blobs are stored in git.

## Frontend

```powershell
cd frontend
npm install
npm test
```

Frontend tests cover:

- file extension and size validation permutations
- API response parsing and image URL building
- foreign-origin URL rejection

## Manual smoke checklist

After changing alignment or differencing logic, verify with real drawings:

1. Compare two revisions of a real PDF drawing.
2. Compare a PNG against a PDF of the same drawing.
3. Re-upload a file and confirm the previous result disappears before comparing again.
4. Download the comparison PNG from the result viewer.
5. Try a dark-background drawing and inspect false-positive regions.

## CI

GitHub Actions runs on every push and pull request:

- `ruff check backend`
- `pytest backend/tests -v`
- `npm test` and `npm run build` in `frontend/`
