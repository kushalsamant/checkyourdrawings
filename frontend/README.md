# Frontend

React + TypeScript UI for Check Your Drawings.

## Development

```powershell
npm install
npm run dev
```

Open **http://127.0.0.1:5173**. The Vite dev server proxies `/compare`, `/outputs`, and `/health` to `http://127.0.0.1:8000`.

Leave `VITE_API_BASE_URL` unset in local dev (see `.env.example`).

For local sign-in, set `VITE_KVSHVL_AUTH_URL` in `frontend/.env` (production uses Vercel env vars).

## Production build

```powershell
$env:VITE_API_BASE_URL="https://checkyourdrawings.onrender.com"
$env:VITE_KVSHVL_AUTH_URL="https://auth.kvshvl.in"
npm run build
```

## Tests

```powershell
npm test
```
