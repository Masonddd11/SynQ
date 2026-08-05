# SynQ — Agent Guide

AI-powered swing trading analysis platform. Three-layer signal stack: LLM agents (fundamental/sentiment/news), MiroFish GraphRAG (knowledge graph), and a proprietary swing trade indicator — fused into a confluence score.

## Repo Structure

```
SynQ/
├── backend/          # FastAPI (Python 3.11+)
│   ├── app/
│   │   ├── main.py         # FastAPI app, CORS, router registration
│   │   ├── config.py       # Pydantic Settings (env-based)
│   │   ├── routers/        # API routes: stocks, analyses, watchlist, alerts, user
│   │   ├── models/         # Pydantic models (CamelModel base → camelCase JSON)
│   │   └── modules/        # Domain logic
│   │       ├── agents/     # LLM agents: fundamental, sentiment, news, synthesis
│   │       ├── graphrag/   # Knowledge graph: ingestion, graph, report
│   │       └── indicator/  # Swing indicator: momentum, volume, structure, confluence
│   ├── tests/              # pytest (asyncio_mode=auto)
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/         # Next.js 16.3 + React 19 + Tailwind v4
│   ├── src/
│   │   ├── app/            # App Router (layout, page, globals.css)
│   │   ├── components/ui/  # shadcn components (base-nova style)
│   │   └── lib/            # api.ts, supabase.ts, utils.ts (cn helper)
│   ├── package.json        # Bun 1.3.14 packageManager
│   └── components.json     # shadcn config
├── docs/
│   ├── api/ENDPOINTS.md    # API reference
│   ├── db/schema.sql       # PostgreSQL schema (source of truth for data model)
│   └── PRD.md              # Product requirements
├── docker-compose.yml      # postgres + redis + api
└── .env.example            # Required env vars
```

## Commands

### Backend

```bash
cd backend
# Run server (requires .env with DATABASE_URL, REDIS_URL, API keys)
uvicorn app.main:app --reload --port 8000

# Lint
ruff check .
ruff format .

# Type check
mypy app/

# Tests
pytest                       # all tests
pytest tests/test_health.py  # single file
pytest -k "test_name"        # single test by name
```

### Frontend

```bash
cd frontend
bun dev          # dev server on :3000
bun run build   # production build
bun run lint    # eslint (core-web-vitals + typescript)
```

### Docker (full dev stack)

```bash
docker compose up            # postgres:5432, redis:6379, api:8000
docker compose up postgres   # just the database
```

## Key Conventions

### Backend

- **Pydantic models** use `CamelModel` base class (`app/models/base.py`) — Python snake_case fields serialize to camelCase JSON for the frontend. Use `populate_by_name=True` so both snake and camel work.
- **Ruff** config: line-length 100, target py311, selects E/F/I/N/W/UP.
- **mypy** is strict mode (`python_version = "3.11"`).
- **pytest** runs with `asyncio_mode = "auto"` — async tests don't need `@pytest.mark.asyncio`.
- **CORS** allows `http://localhost:3000` only.
- Routers are registered in `app/main.py` with `/api` prefix.
- **Current state**: Routers return mock/in-memory data (TODO markers present). Real DB integration pending.

### Frontend

- **Next.js 16.3** — NOT an older version. Check `node_modules/next/dist/docs/` before writing Next.js code; APIs may differ from your training data.
- **React 19** — not 18.
- **Tailwind v4** — uses `@tailwindcss/postcss` plugin (not v3 config). No `tailwind.config.*` file; theming is in `src/app/globals.css`.
- **shadcn** with `base-nova` style. Add components via `npx shadcn@latest add <component>`. Components land in `src/components/ui/`.
- **Path alias**: `@/*` → `./src/*`.
- **Package manager**: Bun. `bun.lock` is committed. Do not generate `package-lock.json` or `yarn.lock`.
- **ESLint**: flat config with `eslint-config-next/core-web-vitals` + `eslint-config-next/typescript`.
- **API client**: `src/lib/api.ts` — typed wrappers for all backend endpoints. Base URL from `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).
- **Supabase client**: `src/lib/supabase.ts` — browser client using `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

### Database

- **Schema source of truth**: `docs/db/schema.sql` — always read this for column names and constraints before writing queries or models.
- Tables: `stocks`, `profiles` (extends Supabase `auth.users`), `analyses`, `watchlist`, `alerts`.
- Alert types (DB constraint): `score_change`, `signal_change`, `price_target`, `earnings_warning`, `news_spike`.

## Env Vars

Backend (`.env`): `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `REDIS_URL`, `DATABASE_URL`.

Frontend (`.env.local`): `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`), `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

## Gotchas

- `frontend/AGENTS.md` is auto-managed by `next dev` (regenerates the Next.js agent rules block). Do not edit it manually.
- Backend models and routers are scaffolded but data is mocked — expect TODO comments and placeholder implementations.
- Supabase auth is handled on the frontend; backend validates JWTs. All API endpoints require `Authorization: Bearer <supabase_jwt>` except `/health` and stock listing.
- The `frontend/` and `backend/` directories are independent — no shared workspace tooling (no root `package.json`, no root `pyproject.toml`).
