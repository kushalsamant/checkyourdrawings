# Frontend

React + TypeScript UI for Check Your Drawings (Vite 7, React 19).

## Routes

Manual routing in `src/main.tsx` (no React Router):

| Path | Page |
|------|------|
| `/` | Compare (`App.tsx`) — upload two PDFs, view overlay |
| `/about` | About — body from repo root [index.md](../index.md) |
| `/pricing` | Usage limits and Pro checkout (`PricingPage.tsx`) |
| `/account` | Plan and subscription (`AccountPage.tsx`) |
| `/auth/callback` | OAuth return from [auth.kvshvl.in](https://auth.kvshvl.in) |

## Styling

Platform chrome comes from [`platform-design-system`](../../platform-design-system):

| Import | Purpose |
|--------|---------|
| `tokens.css` + `base.css` + `pages.css` | Shared layout, header, pricing, account, about |
| `src/compare.css` | Compare UI only (upload, viewer, overlay legend) |

Nav links live in `src/lib/site-chrome.ts`. Pages use `PlatformAppLayout` (wraps package `AppLayout` + auth actions).

## User-facing copy

Copy follows the workspace **6×6 rule** (short lines, pain-first, decision-support — no guarantee language).

| Location | What |
|----------|------|
| [index.md](../index.md) | About page body (markdown → `about-markdown.tsx`) |
| `src/pages/*Page.tsx` | Page `title` / `subtitle` passed to `PlatformAppLayout` |
| `src/lib/site-chrome.ts` | Header nav links |
| `src/App.tsx`, `src/components/*` | Compare flow labels, errors, empty states |
| `frontend/index.html` | Document title and meta description |

Do not duplicate header nav (Compare, Pricing, Account) in page body copy.

## Auth (optional)

Sign-in is **not** required to compare. When configured:

- Set `VITE_KVSHVL_AUTH_URL=https://auth.kvshvl.in` (production) or your local auth dev URL.
- Sign-in redirects to auth → Google → handoff → `/auth/callback` stores a platform JWT in `sessionStorage`.
- The token is sent as `Authorization: Bearer …` on `/compare` and `/jobs/*` when present.
- `/account` and `/payments/*` call **platform-api** via `VITE_PLATFORM_API_URL`, not the Vite proxy.
- Expired tokens are dropped client-side; the app falls back to anonymous compare until the allowance is used.
- Anonymous visitors send a persistent `X-Anon-Session` header (`localStorage`).

## Development

```powershell
npm install
npm run dev
```

Open **http://127.0.0.1:5173**. The dev server proxies `/compare`, `/jobs`, `/allowance`, `/outputs`, and `/health` to `http://127.0.0.1:8000`.

Leave `VITE_API_BASE_URL` **unset** in local dev so requests use relative URLs and the proxy.

Backend requires **Python 3.12** — see root [README.md](../README.md).

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
