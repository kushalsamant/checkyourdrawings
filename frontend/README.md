# Frontend

React + TypeScript UI for Check Your Drawings.

## Development

```powershell
npm install
npm run dev
```

Open **http://127.0.0.1:5173**. The Vite dev server proxies `/compare`, `/outputs`, and `/health` to `http://127.0.0.1:8000`.

Leave `VITE_API_BASE_URL` unset in local dev (see `.env.example`).

## Production build

```powershell
$env:VITE_API_BASE_URL="https://api.example.com"
npm run build
```

## Tests

```powershell
npm test
```
