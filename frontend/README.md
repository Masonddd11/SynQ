# Jings Street — Frontend

Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS v4 dashboard for the
swing trading agent. The FastAPI backend on `:8000` remains the API server — Next.js
proxies every `/api/*` request to it during development.

## Stack

- **Next.js 15** App Router — file-system routing, `app/` directory
- **React 19** — pages are client components (`'use client'`) that poll the API
- **Tailwind CSS v4** — CSS-first config in `src/index.css` (no `tailwind.config`)
- **shadcn/ui "base-nova"** primitives (`@base-ui/react`) in `src/components/ui/`
- **recharts** charts, **lucide-react** icons, **Geist** variable font

## Getting started

```bash
# From the repo root: start the FastAPI backend on :8000
python -m uvicorn api.server:app --app-dir . --reload

# Then, in this directory: install and start Next.js on :3000
npm install
npm run dev
```

Open http://localhost:3000.

Or run both at once from `frontend/`:

```bash
npm run dev:all
```

## Scripts

| Script | Purpose |
|---|---|
| `npm run dev` | Next.js dev server on :3000 (proxies `/api` → :8000) |
| `npm run dev:api` | FastAPI backend on :8000 with reload |
| `npm run dev:all` | Both, via `concurrently` |
| `npm run build` | Production build (type-checks + compiles) |
| `npm run start` | Serve the production build on :3000 |
| `npm run lint` | ESLint (`next lint`, eslint-config-next) |

## Layout

```
app/                    # App Router routes (thin server wrappers)
  layout.tsx            # Root layout — metadata, font, global CSS, nav shell
  page.tsx              # /      → Backtest session history
  new/page.tsx          # /new   → New backtest form
  analysis/page.tsx     # /analysis → Multi-session analysis
  data/page.tsx         # /data  → Fixture data refresh
  sessions/[sessionId]/page.tsx  # /sessions/:id → Session detail
  live/paper/page.tsx   # /live/paper → Paper trading
  live/real/page.tsx    # /live/real → Live trading (stub)
  settings/page.tsx     # /settings → Model, API keys, playbook
  icon.svg              # Favicon
src/
  components/           # Layout shell, metric cards, tabs, ui/ primitives
  lib/                  # api.ts (typed API client), format.ts helpers
  pages/                # Client page components (one per route)
  index.css             # Tailwind v4 + design tokens
```

## API proxy

`next.config.ts` rewrites `/api/:path*` to `http://localhost:8000/api/:path*`.
The backend target is fixed at `localhost:8000` — the FastAPI app lives in the
repo root (`api/server.py`) and is **not** bundled with the frontend.
