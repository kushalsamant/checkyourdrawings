# Frontend

React + TypeScript UI for Check Your Drawings (Vite 7, React 19).

## Routes

Manual routing in `src/main.tsx` (no React Router):

| Path | Page |
|------|------|
| `/` | Compare app (`App.tsx`) — upload two PDFs, view overlay |
| `/about` | About content from repo root [index.md](../index.md) |
| `/auth/callback` | OAuth return from [auth.kvshvl.in](https://auth.kvshvl.in); stores platform JWT in `sessionStorage` |

## Auth (optional)

Sign-in is **not** required to compare. When configured:

- Set `VITE_KVSHVL_AUTH_URL=https://auth.kvshvl.in` (production) or your local auth dev URL.
- Sign-in redirects to auth → Google → handoff with a short-lived `handoff_code` → `/auth/callback` exchanges it for a platform JWT → home.
- The token is sent as `Authorization: Bearer …` on `/compare` and `/account` when present.
- Expired tokens are dropped client-side; the app falls back to anonymous compare until the anonymous allowance is exhausted.
- Anonymous visitors receive a persistent `X-Anon-Session` header (stored in `localStorage`).

## Development

```powershell
npm install
npm run dev
```

Open **http://127.0.0.1:5173**. The dev server proxies `/compare`, `/jobs`, `/allowance`, `/outputs`, and `/health` to `http://127.0.0.1:8000`.

Leave `VITE_API_BASE_URL` **unset** in local dev so requests use relative URLs and the proxy.

For optional sign-in locally, use production auth (local auth does not support `localhost` return URLs):

```env
VITE_KVSHVL_AUTH_URL=https://auth.kvshvl.in
```

## Production build

Vercel sets env vars; locally:

```powershell
$env:VITE_API_BASE_URL="https://checkyourdrawings.onrender.com"
$env:VITE_KVSHVL_AUTH_URL="https://auth.kvshvl.in"
npm run build
```

Output: `frontend/dist` (see root [vercel.json](../vercel.json)).

## Tests

```powershell
npm test
```

Vitest + jsdom (`src/**/*.test.ts`).
