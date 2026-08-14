## 🗺️ Development Roadmap

A milestone-based roadmap for contributors, structured like a normal sprint-based development plan. Each milestone has a goal, estimated effort, dependencies, and a detailed checklist. Milestones are sequential unless marked otherwise — later work assumes earlier milestones are functional (not necessarily polished).

### Roadmap Map

```
 M0                M1              M2               M3                M4
 Setup    ───▶   Domain    ───▶  Provider   ───▶   Adapters   ───▶  Aggregation
 & CI            Models          Clients          (Normalize)        + Cache
                                                                          │
                                                                          ▼
 M8               M7              M6               M5
 Deploy   ◀───  Testing   ◀───  Frontend   ◀───    API Layer
 & Docs          & QA            Foundation        (/jobs endpoint)

 ─────────────────────────────────────────────────────────────────▶ time
```

Backend track: `M0 → M1 → M2 → M3 → M4 → M5`
Frontend track: `M0 → M6` (can start once M5's OpenAPI schema is stable, or in parallel against a mocked contract)
Both converge at: `M7 → M8`

| Milestone | Goal | Est. effort | Depends on |
|---|---|---|---|
| **M0** — Setup & CI | Repo, tooling, CI pipelines running | 2–3 days | — |
| **M1** — Domain Models | Unified `JobPosting` contract defined & tested | 1–2 days | M0 |
| **M2** — Provider Clients | Adzuna + Jooble raw data fetchable | 2–3 days | M1 |
| **M3** — Adapters | Raw payloads normalized into `JobPosting` | 2–3 days | M2 |
| **M4** — Aggregation & Cache | Combined, deduped, cached results | 2–3 days | M3 |
| **M5** — API Layer | Public `/api/v1/jobs` endpoint live | 2 days | M4 |
| **M6** — Frontend Foundation | Working search UI against the API | 4–5 days | M5 (or mocked contract, in parallel) |
| **M7** — Testing & QA | Coverage, E2E, contract & load tests | 3–4 days | M5, M6 |
| **M8** — Deploy & Docs | Dockerized, documented, ready to ship | 2–3 days | M7 |

*(Effort estimates assume one contributor per milestone working part-time; parallelize across contributors where dependencies allow — e.g., M2's two clients can be split between two people.)*

---

### M0 — Setup & CI

**Goal:** anyone can clone the repo and run both services locally with one command.

- [ ] Initialize monorepo structure (`backend/`, `temp_frontend/`, `shared/`)
- [ ] `backend`: set up `pyproject.toml` with `uv`, pin Python 3.14
- [ ] `backend`: add base dependencies (`fastapi[standard]`, `httpx`, `pydantic`, `pytest`, `pytest-asyncio`)
- [ ] `frontend`: scaffold with `create-next-app` (TypeScript, App Router, Tailwind)
- [ ] Add root `docker-compose.yml` wiring backend + frontend for local dev
- [ ] Add `.env.example` files for both backend and frontend (API keys, base URLs)
- [ ] Set up `ruff` + `mypy` (backend) and `eslint` + `tsc --noEmit` (frontend) as lint/typecheck gates
- [ ] Add `.github/workflows/backend-ci.yml` and `frontend-ci.yml` (lint, typecheck, test on PR)

**Definition of done:** `docker-compose up` starts both services; CI runs green on an empty PR.

### M1 — Domain Models

**Goal:** the shape of a "job posting" is settled and won't need to change once providers are wired in.

- [ ] Define unified `JobPosting` Pydantic model (`backend/app/models/job.py`) — id, title, company, location, salary_min/max, currency, url, source, posted_date, description_snippet
- [ ] Define `JobQuery` request schema (`backend/app/models/query.py`) — keyword, location, page, page_size, remote_only, salary_min
- [x] Define standardized `JobListResponse` (results, total_count, page, cached: bool)
- [ ] Write unit tests asserting model validation edge cases (missing salary, malformed URL, empty keyword)

**Definition of done:** `JobPosting`/`JobQuery`/`JobListResponse` merged and reviewed — treat this as a frozen contract for the rest of the backend track.

### M2 — Provider Clients

**Goal:** raw JSON from Adzuna and Jooble can be fetched reliably, independent of each other.

- [ ] Implement `base_client.py` — shared `httpx.AsyncClient` factory with timeout + retry (e.g. `tenacity` or manual backoff)
- [ ] Implement `adzuna_client.py` — GET request, `app_id`/`app_key` auth, pagination params
- [x] Implement `jooble_client.py` — POST request, JSON body, API key handling
- [ ] Add per-client error handling (timeout, 4xx, 5xx) → raise typed exceptions from `core/exceptions.py`
- [ ] Mock both providers in tests using recorded fixture JSON (`tests/fixtures/`)
- [ ] Unit test: client returns typed raw response even on partial/malformed provider payloads

**Definition of done:** each client can be called standalone in a test and returns raw provider JSON or a typed error — no normalization yet.

*(Parallelizable: one contributor per client.)*

### M3 — Adapters (Normalization Layer)

**Goal:** raw provider payloads become valid `JobPosting` objects, one adapter per provider.

- [ ] Define `base_adapter.py` interface (`Protocol` with `normalize(raw: dict) -> list[JobPosting]`)
- [ ] Implement `adzuna_adapter.py` — map Adzuna fields → `JobPosting`, strip HTML from description
- [ ] Implement `jooble_adapter.py` — map Jooble fields → `JobPosting`, normalize salary string → min/max numeric
- [x] Handle missing/optional fields gracefully (fallback values, never raise on missing salary)
- [ ] Unit tests per adapter using fixture payloads — assert exact `JobPosting` output

**Definition of done:** feeding a saved fixture response through each adapter produces a correct, fully-typed list of `JobPosting`.

### M4 — Aggregation, Dedup & Cache

**Goal:** a single query returns one clean, deduped, cached list — regardless of how many providers are behind it.

- [ ] Implement `aggregator.py` — `asyncio.gather` across all registered clients + adapters, with per-provider failure isolation (one provider failing shouldn't fail the whole request)
- [ ] Implement `deduplicator.py` — hash on normalized URL, fallback to `title + company` fuzzy match
- [ ] Implement `ttl_cache.py` — simple in-memory TTL cache keyed by normalized query params
- [ ] Wire cache into the request flow (check cache → miss → fetch → normalize → dedup → cache → return)
- [ ] Unit tests: dedup correctness with overlapping mock results from both providers
- [ ] Unit tests: cache hit/miss/expiry behavior

**Definition of done:** calling the aggregator service directly (no HTTP layer yet) returns a correct, deduped `JobListResponse` from mocked clients.

### M5 — API Layer

**Goal:** the gateway is reachable over HTTP and its contract (OpenAPI schema) is stable enough for the frontend to consume.

- [ ] Implement `GET /api/v1/jobs` route with query param validation
- [ ] Wire dependency injection for cache instance and aggregator service
- [ ] Add OpenAPI metadata (descriptions, examples) for all request/response models — this feeds the frontend type generation
- [ ] Add global exception handlers (provider timeout, invalid query, no results)
- [ ] Integration test: full request against mocked provider clients, asserting final JSON shape
- [ ] Add basic rate-limit / request-size guardrails on the public endpoint

**Definition of done:** `curl localhost:8000/api/v1/jobs?keyword=QA&location=Berlin` returns real (or mocked) results; `/openapi.json` is stable and exported to `shared/`.

*🔀 Frontend work (M6) can branch off here — or earlier, against a hand-written mock schema, if you want both tracks running in parallel from M0.*

### M6 — Frontend Foundation

**Goal:** a working search UI that talks to the real API.

- [ ] Run `openapi-typescript` against backend's `/openapi.json` → generate `temp_frontend/types/job.ts`
- [ ] Implement `lib/api-client.ts` — typed fetch wrapper for `/api/v1/jobs`
- [ ] Set up `TanStack Query` provider in `app/layout.tsx`
- [ ] Build `JobFilters.tsx` (keyword, location, remote toggle, salary min)
- [ ] Build `JobCard.tsx` and `JobList.tsx` (results rendering, loading/empty states)
- [ ] Wire `app/jobs/page.tsx` as a Server Component that fetches initial results, with client-side refetch on filter change
- [ ] Add `loading.tsx` skeleton state

**Definition of done:** a user can type a keyword + location in the browser and see real deduped results from both providers.

### M7 — Testing & Quality

**Goal:** confidence that the system behaves correctly and won't silently break on upstream API changes.

- [ ] Backend: reach meaningful coverage on `adapters/`, `services/` (target ~90%+, these are pure logic)
- [ ] Frontend: Vitest unit tests for `JobCard`, `JobFilters`, `useJobSearch`
- [ ] Frontend: Playwright E2E — search flow, empty state, error state
- [ ] Add contract test: validate live (or recorded) provider responses still match adapter assumptions (catches upstream API drift)
- [ ] Add basic load test on `/api/v1/jobs` (e.g. `locust` or `k6`) to validate cache effectiveness under repeated queries

**Definition of done:** CI enforces coverage thresholds; E2E suite passes against a locally running full stack.

### M8 — Deployment & Docs

**Goal:** anyone (including future contributors) can deploy this from a clean checkout.

- [ ] Write backend `Dockerfile` (multi-stage: build deps with `uv`, slim runtime image)
- [ ] Write frontend `Dockerfile` (Next.js standalone output mode)
- [ ] Finalize `docker-compose.yml` for local full-stack dev (backend + frontend + optional Redis)
- [ ] Document environment variables in both `.env.example` files
- [ ] Add `CONTRIBUTING.md` (branching strategy, commit conventions, how to run tests locally)
- [ ] Expand this `README.md` with setup/run instructions

**Definition of done:** a fresh clone + `docker-compose up` + documented env vars = working full stack, no tribal knowledge required.

---

### Stretch Goals (post-MVP)

- [ ] Swap in-memory cache for Redis to support multi-instance deployment
- [ ] Add a third provider (e.g. Reed, Remotive, LinkedIn Jobs API) to validate the Adapter Pattern's extensibility
- [ ] Add saved-search / email-alert feature
- [ ] Add pagination cursor support instead of offset-based paging
- [ ] Add i18n on the frontend (given the DE/PL/EU coverage focus)

---



Since the pairing is **TypeScript on the frontend + Python on the backend**, here's a stack using current stable releases. Versions move fast — pin exact ones in `package.json` / `pyproject.toml` at implementation time and re-check before a production build.

### Backend — Python

| Component | Choice | Notes |
|---|---|---|
| Runtime | **Python 3.14** (latest patch: 3.14.7) | Ships PEP 649/749 deferred annotation evaluation — big win for Pydantic-heavy apps; also has a stable external debugger interface (PEP 768) |
| Framework | **FastAPI 0.141.x** | Current release line on PyPI; still the fastest-growing async Python framework, ~490M monthly downloads |
| Validation | **Pydantic v2** | Already implied by FastAPI; keep on latest 2.x |
| HTTP client | **httpx** (async) | For concurrent Adzuna/Jooble calls via `asyncio.gather` |
| ASGI server | **Uvicorn** (or Hypercorn if HTTP/2 is needed) | |
| Package manager | **uv** | Now the FastAPI-recommended installer/runner — much faster than pip/poetry for CI |
| Testing | **pytest** + **pytest-asyncio** | |
| Optional cache upgrade | Redis (if moving past in-memory TTL cache to multi-instance deployments) | |

### Frontend — TypeScript

| Component | Choice | Notes |
|---|---|---|
| Language | **TypeScript 7.0** | New Go-based native compiler (`tsc` rewritten for speed) — large compile-time speedups over TS 5/6 |
| Framework | **Next.js 16.3** | Turbopack is stable and now the default bundler for both `dev` and `build`; Build Adapters API for non-Vercel hosting |
| UI library | **React 19.2** | Ships with the React Compiler (stable as of 19.2), reducing manual `useMemo`/`useCallback` |
| Runtime | **Node.js 24 (Active LTS)** | Safer default for production than Node 26, which is still on the "Current" track until it enters LTS in Oct 2026 |
| Styling | Tailwind CSS (latest 4.x) | Pairs well with Next.js App Router |
| Data fetching | Native `fetch` + React Server Components, or TanStack Query for client-side caching of `/api/v1/jobs` | |
| Testing | Vitest + Playwright | |

### Why this pairing works well here

- **TS 7's native compiler** + **Next.js 16's Turbopack** minimize the frontend build/type-check bottleneck when iterating on the job-search UI.
- **FastAPI + Pydantic v2** on 3.14 keeps the backend's typed contracts (your unified `JobPosting` model) consistent end-to-end — you could even generate the TS client types from FastAPI's OpenAPI schema (`openapi-typescript`) to avoid hand-duplicating the `JobPosting` shape on the frontend.
- **uv** on the backend and **Turbopack** on the frontend both target the same pain point (slow tooling) — worth adopting together for a snappy dev loop.

---

## 📁 Suggested Project Structure

Full-stack monorepo layout — Python/FastAPI backend + TypeScript/Next.js frontend, sharing a single OpenAPI-generated contract:

```
job-integration-gateway/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entrypoint, router registration
│   │   ├── config.py                # Settings via pydantic-settings (.env, API keys, TTL)
│   │   │
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── routes_jobs.py   # /api/v1/jobs endpoint(s)
│   │   │       └── dependencies.py  # Shared deps (cache instance, query params)
│   │   │
│   │   ├── clients/
│   │   │   ├── base_client.py       # Shared async httpx client + retry/timeout logic
│   │   │   ├── adzuna_client.py     # Adzuna-specific request logic (GET + auth params)
│   │   │   └── jooble_client.py     # Jooble-specific request logic (POST + body)
│   │   │
│   │   ├── adapters/
│   │   │   ├── base_adapter.py      # Adapter interface (Protocol/ABC)
│   │   │   ├── adzuna_adapter.py    # Maps Adzuna payload -> unified JobPosting model
│   │   │   └── jooble_adapter.py    # Maps Jooble payload -> unified JobPosting model
│   │   │
│   │   ├── services/
│   │   │   ├── aggregator.py        # asyncio.gather orchestration across clients
│   │   │   └── deduplicator.py      # URL / title+company hashing & merge logic
│   │   │
│   │   ├── cache/
│   │   │   └── ttl_cache.py         # In-memory TTL cache implementation
│   │   │
│   │   ├── models/
│   │   │   ├── job.py               # Unified JobPosting Pydantic schema
│   │   │   └── query.py             # Request/query param schema
│   │   │
│   │   └── core/
│   │       ├── exceptions.py        # Custom exception classes + handlers
│   │       └── logging.py           # Structured logging setup
│   │
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_adapters.py
│   │   │   ├── test_deduplicator.py
│   │   │   └── test_ttl_cache.py
│   │   ├── integration/
│   │   │   └── test_jobs_endpoint.py
│   │   └── fixtures/
│   │       ├── adzuna_response.json
│   │       └── jooble_response.json
│   │
│   ├── .env.example
│   ├── pyproject.toml               # managed via uv
│   └── Dockerfile
│
├── frontend/
│   ├── app/                         # Next.js App Router
│   │   ├── layout.tsx
│   │   ├── page.tsx                 # Job search landing page
│   │   ├── jobs/
│   │   │   ├── page.tsx             # Job results page (RSC, fetches /api/v1/jobs)
│   │   │   └── loading.tsx
│   │   └── api/                     # Optional: Next.js route handlers / BFF proxy
│   │       └── jobs/route.ts
│   │
│   ├── components/
│   │   ├── ui/                      # Reusable primitives (button, input, card)
│   │   ├── JobCard.tsx
│   │   ├── JobFilters.tsx
│   │   └── JobList.tsx
│   │
│   ├── lib/
│   │   ├── api-client.ts            # Typed fetch wrapper for the FastAPI gateway
│   │   └── query-client.ts          # TanStack Query setup
│   │
│   ├── types/
│   │   └── job.ts                   # Generated from backend OpenAPI schema (openapi-typescript)
│   │
│   ├── hooks/
│   │   └── useJobSearch.ts
│   │
│   ├── tests/
│   │   ├── unit/                    # Vitest component/unit tests
│   │   └── e2e/                     # Playwright end-to-end tests
│   │
│   ├── public/
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── Dockerfile
│
├── shared/
│   └── openapi.json                 # Exported from FastAPI, consumed by openapi-typescript
│
├── docker-compose.yml               # Runs backend + frontend together for local dev
├── .github/
│   └── workflows/
│       ├── backend-ci.yml           # pytest, ruff/mypy, uv sync
│       └── frontend-ci.yml          # vitest, eslint, tsc, playwright
└── README.md
```

**Layering rationale (backend):**

| Layer | Responsibility | Why separated |
|---|---|---|
| `api/` | HTTP concerns only (routing, validation, status codes) | Keeps transport logic out of business logic |
| `clients/` | Talking to external providers | One client per provider — isolated failure/retry handling |
| `adapters/` | Normalizing provider payloads | Adapter Pattern — new provider = new adapter, no changes elsewhere |
| `services/` | Orchestration, aggregation, dedup | Pure business logic, easily unit-testable without HTTP |
| `cache/` | Storage concern | Swappable later for Redis without touching services |
| `models/` | Shared contracts | Single source of truth for the unified schema |

**Frontend/backend contract:**

The `shared/openapi.json` file is exported from FastAPI (`/openapi.json`) and fed into `openapi-typescript` to generate `temp_frontend/types/job.ts`. This keeps the `JobPosting` shape defined once, in the backend, with the frontend's TypeScript types always in sync — no manual duplication or drift between the two codebases.

This keeps the **Adapter Pattern** front and center: adding a third provider (e.g., Reed, LinkedIn Jobs API) means adding one `clients/*_client.py` + one `adapters/*_adapter.py`, and registering it in `aggregator.py` — no other layer changes, and the frontend picks up new fields automatically once the OpenAPI schema is regenerated.
