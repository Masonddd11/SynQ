# SynQ API Endpoints

Quick reference derived from `openapi.yaml` and `docs/db/schema.sql`.

**Source of truth:** `docs/db/schema.sql` defines the data. The API mirrors it.

---

## Auth

All endpoints require `Authorization: Bearer <supabase_jwt>` header.
Auth is handled by Supabase on the frontend — backend validates the JWT.

---

## Stocks (`stocks` table)

| Method | Endpoint | DB Operation | Auth |
|--------|----------|--------------|------|
| `GET` | `/api/stocks` | SELECT stocks (paginated, searchable) | Public |
| `GET` | `/api/stocks/{ticker}` | SELECT stock by ticker | Public |

---

## Analyses (`analyses` table)

| Method | Endpoint | DB Operation |
|--------|----------|--------------|
| `POST` | `/api/analyses` | INSERT analysis (status: pending) |
| `GET` | `/api/analyses` | SELECT analyses (paginated, filtered) |
| `GET` | `/api/analyses/{id}` | SELECT analysis by id |
| `GET` | `/api/analyses/latest?ticker=X` | SELECT latest analysis for ticker |

**Flow:**
1. `POST` returns `{ id, status: "pending" }`
2. Backend enqueues async job (FastAPI BackgroundTasks)
3. Job runs three layers, updates row to `completed`
4. `GET /analyses/{id}` returns full results

---

## Watchlist (`watchlist` table)

| Method | Endpoint | DB Operation |
|--------|----------|--------------|
| `GET` | `/api/watchlist` | SELECT watchlist |
| `POST` | `/api/watchlist` | INSERT watchlist item |
| `PATCH` | `/api/watchlist/{id}` | UPDATE watchlist item |
| `DELETE` | `/api/watchlist/{id}` | DELETE watchlist item |

---

## Alerts (`alerts` table)

| Method | Endpoint | DB Operation |
|--------|----------|--------------|
| `GET` | `/api/alerts` | SELECT alerts |
| `POST` | `/api/alerts` | INSERT alert rule |
| `PATCH` | `/api/alerts/{id}` | UPDATE alert (threshold, isActive) |
| `DELETE` | `/api/alerts/{id}` | DELETE alert |

**Alert types** (from schema CHECK constraint):
- `score_change` — confluence score changes by threshold
- `signal_change` — signal flips
- `price_target` — price hits target
- `earnings_warning` — earnings approaching
- `news_spike` — unusual news activity

---

## User (`profiles` table)

| Method | Endpoint | DB Operation |
|--------|----------|--------------|
| `GET` | `/api/user/profile` | SELECT profile |
| `PATCH` | `/api/user/profile` | UPDATE profile (fullName) |
| `GET` | `/api/user/subscription` | SELECT tier + usage |

---

## System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check (no auth) |

---

## Error Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable",
    "details": {}
  }
}
```

| Status | Code | When |
|--------|------|------|
| 400 | VALIDATION_ERROR | Bad request body |
| 401 | UNAUTHORIZED | Missing/invalid JWT |
| 404 | NOT_FOUND | Resource doesn't exist |
| 409 | CONFLICT | Duplicate (e.g., ticker already in watchlist) |
| 429 | RATE_LIMIT_EXCEEDED | Daily analysis limit hit |
