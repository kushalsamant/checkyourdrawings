# Check Your Drawings

Check Your Drawings is a local MVP for comparing two drawing revisions. It accepts PDF, PNG, JPG, or JPEG files, aligns Revision B onto Revision A, detects visual changes, classifies regions as additions, deletions, or modifications, and renders a downloadable comparison image.

## Architecture

- React + TypeScript frontend in `frontend/`
- FastAPI backend in `backend/`
- OpenCV/NumPy computer vision pipeline in `backend/app/services/`
- Generated comparison images served from `http://127.0.0.1:8000/outputs/...`

## Backend

```powershell
cd C:\Users\ADMIN\Documents\GitHub\checkyourdrawings
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --reload
```

Health check:

```powershell
curl http://127.0.0.1:8000/health
```

## Frontend

```powershell
cd C:\Users\ADMIN\Documents\GitHub\checkyourdrawings\frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Pipeline

1. Upload Revision A and Revision B.
2. Convert PDF or image inputs into image arrays.
3. Align Revision B onto Revision A using ORB features and RANSAC homography.
4. Detect meaningful changed regions with thresholding, morphology, and contours.
5. Render a final comparison image with green additions, red deletions, and yellow modifications.
