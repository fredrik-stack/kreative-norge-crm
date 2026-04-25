# Frontend (Editor UI)

React + Vite frontend for the Django/DRF editor API.

## Environment

The frontend reads `VITE_API_BASE` from Vite env vars.

- Empty (default): same-origin requests (`/api/...`) via reverse proxy or same host
- Local dev against Django on another port: `VITE_API_BASE=http://localhost:8000`
- Staging/prod on separate API domain: set full HTTPS API origin

Copy `frontend/.env.example` to `frontend/.env.local` (dev) or set the variable in your deploy platform.

## Auth and CSRF

- Uses Django session auth (`/api/auth/*`)
- Write requests send `X-CSRFToken` from `csrftoken` cookie
- `fetch(..., { credentials: "same-origin" })` is used, so same-origin deployment is the easiest setup

If frontend and API are served on different origins, configure Django/CORS/cookies accordingly:

- `CSRF_TRUSTED_ORIGINS`
- session cookie settings (`SameSite`, `Secure`)
- CORS (if applicable)

## Commands

```bash
npm run dev
npm run test
npm run build
npm run test:e2e
npm run ci:check
```
