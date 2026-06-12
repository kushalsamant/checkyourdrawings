# Frontend

React + TypeScript interface for uploading two drawing revisions and viewing the generated comparison image.

## Run

```powershell
npm install
npm run dev
```

The frontend expects the backend at `http://127.0.0.1:8000` by default. Override it with:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```
