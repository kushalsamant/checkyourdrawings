# Testing

## Automated tests

### Backend

```powershell
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
pytest backend/tests -v
```

| Area | Coverage |
|------|----------|
| `/compare` integration | PDF-only uploads, content scenarios, margin shift |
| Route errors | 415 for non-PDF, 400 empty/corrupt, 413 oversize |
| Pipeline units | alignment, file validation, overlay renderer, content detection, image limits, output cleanup |

### Frontend

```powershell
cd frontend
npm test
```

Covers PDF-only file validation and API response parsing.

## Manual smoke

See [smoke-test.md](smoke-test.md). Required pair: `0A` + `0B` architectural PDFs at repo root (local only, gitignored).

## Integration markers

Tests marked `@pytest.mark.integration` exercise the full `/compare` route with synthetic PDF fixtures from `backend/tests/fixtures/factory.py`.
