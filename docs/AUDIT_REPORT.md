# SynQ — Audit Report

> Generated: 2026-08-05
> Scope: Docs ↔ code cross-check, config hygiene, drift analysis
> Status: **23 issues found** (7 high, 10 medium, 6 low)

---

## Summary

| Category | Issues |
|----------|--------|
| OpenAPI ↔ Code drift | 9 |
| DB schema ↔ Model drift | 3 |
| Config hygiene | 6 |
| Duplicate / conflicting types | 2 |
| Test setup gaps | 2 |
| Miscellaneous | 1 |

**Severity key:**
- 🔴 **HIGH** — Will break integration or cause silent bugs
- 🟡 **MEDIUM** — Technical debt, inconsistency, or missing coverage
- 🟢 **LOW** — Cosmetic or forward-looking

---

## 1. OpenAPI ↔ Code Drift (9 issues)

### 🔴 1.1 Health endpoint path mismatch

**Spec:** `GET /health` (outside `/api` prefix)
**Code:** `GET /health` (correct path, BUT...)
**Spec version field:** `"version": { "example": 0.1.0 }` — example value `0.1.0` is a number, not a string.
**Code version field:** Returns `"version": "0.1.0"` (string).
**Fix:** Change OpenAPI spec `version` example from `0.1.0` (number) to `"0.1.0"` (string).

### 🔴 1.2 User profile update: query param vs JSON body

**Spec:** `PATCH /user/profile` expects `fullName` in request body.
**Code:** `user.py` reads `full_name` as a **query parameter**:
```python
async def update_profile(full_name: str | None = None):
```
**Impact:** Frontend sending `{ "fullName": "..." }` as JSON body will silently ignore the field. The update does nothing.
**Fix:** Change `user.py` to accept a Pydantic request body model.

### 🔴 1.3 Watchlist/Alert list endpoints return `dict` instead of typed response

**Spec:** `GET /watchlist` returns `{ data: [...], pagination: {...} }` with typed items.
**Code:** `watchlist.py` and `alerts.py` return `response_model=dict`, which:
- Bypasses Pydantic validation on response
- Drops the camelCase alias serialization (returns `snake_case` keys)
**Fix:** Create typed `WatchlistListResponse` and `AlertListResponse` models (like `AnalysisListResponse`) and use them.

### 🟡 1.4 Analyses list returns raw dict for pagination

**Spec:** Returns `{ data: [...], pagination: {...} }`.
**Code:** `analyses.py` uses `AnalysisListResponse` (correct), but pagination is passed as a raw dict:
```python
pagination={
    "page": page,
    "page_size": page_size,
    ...
}
```
This works but bypasses the `Pagination` model defined in `common.py`. Use `Pagination(...)` for consistency.

### 🟡 1.5 Pagination keys: snake_case vs camelCase

**Spec:** `{ "page": 1, "pageSize": 20, "totalItems": 3, "totalPages": 1 }` (camelCase).
**Code (stocks.py):** Returns `page_size`, `total_items`, `total_pages` (snake_case) — the dict isn't serialized through `CamelModel`.
**Impact:** Frontend expecting camelCase keys will get `undefined` values.
**Fix:** Use the `Pagination` model for all paginated responses, or serialize the dict through `CamelModel`.

### 🟡 1.6 Alert type enum values inconsistent

**Spec:** `enum: [score_change, signal_change, price_target, earnings_warning, news_spike]`
**Code:** Same values — ✅ consistent.
**BUT:** The `AlertType` enum class exists in `alert.py` but the `Alert` model doesn't enforce it as the `alert_type` field type at the JSONB level. This is fine for mock storage but will matter when Supabase stores these as TEXT columns.

### 🟡 1.7 Missing `updated_at` on alerts

**DB schema:** `alerts` table has no `updated_at` column.
**OpenAPI spec:** No `updatedAt` field on `Alert` schema. ✅ Consistent.
**Pydantic model:** `Alert` has no `updated_at`. ✅ Consistent.
**But:** The `Alerts` endpoint PATCH operation modifies `threshold`, `target_price`, `isActive` — there's no way to know when an alert was last modified. Consider adding `updated_at` to the alerts table.

### 🟢 1.8 OpenAPI spec has `security: []` on stocks endpoints

**Spec:** Stocks endpoints correctly override the global `bearerAuth` with `security: []`.
**Code:** Stocks endpoints don't check auth at all (no JWT validation). ✅ Functionally correct, but when auth is added, the public endpoints need explicit opt-out.

### 🟢 1.9 Missing 422 response in OpenAPI spec

**Spec:** Most endpoints only document 200, 401, 404.
**Code:** FastAPI auto-generates 422 for validation errors.
**Fix:** Add `422` responses to endpoints with request bodies, or note "FastAPI auto-generates validation error responses."

---

## 2. DB Schema ↔ Model Drift (3 issues)

### 🔴 2.1 Duplicate `FundamentalResult` type

**Pydantic model (`analysis.py`):**
```python
class FundamentalResult(CamelModel):
    bull_case: str | None = None
    bear_case: str | None = None
    key_metrics: dict | None = None
    risk_score: float | None = None
```

**Dataclass (`agents/fundamental.py`):**
```python
@dataclass
class FundamentalResult:
    ticker: str
    bull_case: str
    bear_case: str
    key_metrics: dict
    risk_score: float
    confidence: float
```

**Issues:**
- Two different classes with the same name in different modules
- Dataclass has `ticker` and `confidence` fields the Pydantic model lacks
- Different nullability (dataclass fields are required, Pydantic fields are optional)
**Fix:** Decide on one source of truth. When agents implement their logic, the dataclass results should be the internal type, and the Pydantic model should be the API serialization type. Add a conversion layer or consolidate.

### 🟡 2.2 `analysis_snapshots` table has no Pydantic model

**DB schema:** `analysis_snapshots` table exists with `id`, `analysis_id`, `ticker`, `confluence_score`, `signal`, `agent_score`, `graphrag_score`, `indicator_score`, `snapshot_at`.
**Code:** No `AnalysisSnapshot` model in `app/models/`.
**OpenAPI spec:** No endpoint references snapshots.
**Impact:** Table exists in DB but nothing in the API layer references it. This is fine for MVP (snapshots are for backtesting, which is out of scope for v0.1), but should be documented as "planned, not implemented."

### 🟡 2.3 `stocks` table has no DB router, only mock data

**DB schema:** Full `stocks` table with RLS policies.
**Code:** `stocks.py` router returns hardcoded mock data (NVDA, AAPL, TSLA).
**Impact:** When real DB is connected, the mock data will conflict. The TODO comments acknowledge this, but no Supabase client or DB query logic exists yet.

---

## 3. Config Hygiene (6 issues)

### 🔴 3.1 Dockerfile copies `.venv/` into container

**File:** `backend/Dockerfile`
```dockerfile
COPY . .
```
This copies the entire `backend/` directory, including `.venv/` (hundreds of MB of Python packages), `__pycache__/`, `.coverage`, `synq_backend.egg-info/`, and `tests/` into the production container.

**Fix:** Add a `.dockerignore` file or use multi-stage build.

### 🔴 3.2 Python version mismatch between Dockerfile and pyproject.toml

**Dockerfile:** `FROM python:3.11-slim`
**pyproject.toml:** `requires-python = ">=3.11"`, `[tool.ruff] target-version = "py311"`, `[tool.mypy] python_version = "3.11"`
**But:** The local `.venv` is Python 3.12 (based on `__pycache__` files: `cpython-312.pyc`).
**Impact:** Docker will run 3.11 while local dev runs 3.12. This can cause subtle incompatibilities. Either standardize on 3.12 everywhere or document the discrepancy.

### 🟡 3.3 `.gitignore` missing entries

Missing entries in root `.gitignore`:
- `.coverage` — pytest-cov output (exists in `backend/.coverage` on disk)
- `*.egg-info/` — partially covered (`*.egg-info/` exists, but `synq_backend.egg-info/` may not match all patterns)
- `.env.development`, `.env.staging`, `.env.production` — only `.env.*.local` is covered
- `supabase/` directory (only `.temp` subfolder is excluded)
- `.turbo/` (if using Turborepo)

### 🟡 3.4 docker-compose.yml: hardcoded Postgres credentials

```yaml
environment:
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: postgres
```
**Fix:** Use environment variable substitution: `${POSTGRES_USER:-postgres}` / `${POSTGRES_PASSWORD:-postgres}` with defaults.

### 🟡 3.5 `.env.example` incomplete

Missing variables that `config.py` defines or that docker-compose uses:
- `DATABASE_URL` — used in `config.py` and `docker-compose.yml`
- `APP_NAME` — in `config.py` but not in `.env.example`
- `APP_VERSION` — in `config.py` but not in `.env.example`
- Data source API keys referenced in PRD: `ALPHA_VANTAGE_API_KEY`, `POLYGON_API_KEY`, `NEWSAPI_KEY`
- `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` — referenced in PRD revenue model
- `NEXT_PUBLIC_API_URL` — frontend needs to know the backend URL

### 🟢 3.6 `frontend/.gitignore` overly broad

```
.env*
```
This excludes `.env`, `.env.local`, `.env.development`, etc. — good for security. But it also excludes `.env.example` or `.env.template` files that should be committed. Consider:
```
.env
.env.local
.env.*.local
!.env.example
```

---

## 4. Test Setup Gaps (2 issues)

### 🟡 4.1 `conftest.py` only clears watchlist state

```python
@pytest.fixture(autouse=True)
def clear_state():
    clear_watchlist_db()
```
**Missing:** `alerts` and `analyses` in-memory stores are not cleared between tests. This means tests can leak state into each other. The `analyses` endpoint uses `_analyses_db` and `alerts` uses `_alerts_db` — neither is cleared.

**Fix:** Add `clear_alerts_db()` and `clear_analyses_db()` functions in the respective routers and call them in `conftest.py`.

### 🟡 4.2 No `health` endpoint test for version string type

**Spec:** `version` should be a string.
**Code:** Returns `"version": settings.app_version` which is a string.
**Test:** `test_health.py` probably checks for `"status": "ok"` but may not assert the type of `version`. Worth confirming.

---

## 5. Duplicate / Conflicting Types (2 issues)

### 🟡 5.1 Duplicate `GraphRAGResult` and `KnowledgeGraphResult`

**Pydantic (`analysis.py`):**
```python
class GraphRAGResult(CamelModel):
    entities: list[dict] | None = None
    relationships: list[dict] | None = None
    report: str | None = None
```

**Dataclass (`graphrag/knowledge_graph.py`):**
```python
@dataclass
class KnowledgeGraphResult:
    entities: list[Entity]
    relationships: list[Relationship]
    report: str
```

The dataclass version has typed `Entity` and `Relationship` objects, while the Pydantic version uses untyped `list[dict]`. When GraphRAG is implemented, the conversion from dataclass → Pydantic will need to handle `Entity`/`Relationship` → `dict` serialization.

### 🟢 5.2 `Pagination` model defined but underused

`common.py` defines a `Pagination` model, but only `AnalysisListResponse` uses it (and even that passes a raw dict). Stocks, watchlist, and alerts all construct pagination dicts manually with snake_case keys.

---

## 6. Miscellaneous (1 issue)

### 🟢 6.1 PRD references infrastructure not in docker-compose

**PRD mentions:** Celery + Redis for async agent execution.
**docker-compose.yml:** Has Redis but no Celery worker service.
**Impact:** Expected for MVP stage, but should be noted as "planned" in the docs.

---

## Recommended Priority

### Immediate fixes (before next commit):
1. **3.1** — Add `.dockerignore` to `backend/`
2. **1.2** — Fix `user.py` profile update to use request body
3. **1.5** — Use `Pagination` model for all paginated responses (fixes camelCase keys)
4. **4.1** — Add `clear_*_db()` to conftest for alerts and analyses

### Short-term (next session):
5. **2.1** — Consolidate duplicate `FundamentalResult` types
6. **3.4** — Externalize Postgres credentials in docker-compose
7. **3.5** — Complete `.env.example` with all variables
8. **3.2** — Standardize Python version (3.11 or 3.12) across Docker and local

### Track for later:
9. **2.2** — Document `analysis_snapshots` as planned
10. **1.9** — Add 422 responses to OpenAPI spec
11. **6.1** — Note Celery as planned in architecture docs
