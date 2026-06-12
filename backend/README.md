# Backend

FastAPI service for the Check Your Drawings comparison pipeline.

## Run

```powershell
cd C:\Users\ADMIN\Documents\GitHub\checkyourdrawings
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --reload
```

## Endpoints

- `GET /` returns basic application status.
- `GET /health` returns backend health.
- `POST /compare` accepts multipart files named `revision_a` and `revision_b`.
- `/outputs/{filename}` serves generated comparison images.
