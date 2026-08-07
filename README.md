# 🌐 Job Integration Gateway

An asynchronous Python-based integration gateway built with **FastAPI** that aggregates, normalizes, and serves job postings from multiple external REST APIs (Adzuna and Jooble) in real time.

This project demonstrates practical integration patterns, including concurrent API orchestration, payload normalization (Adapter Pattern), schema validation using Pydantic, and in-memory response caching.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## ✨ Features

- **Concurrent API Orchestration** — Uses `asyncio.gather` and `httpx` to fetch data from multiple REST endpoints in parallel.
- **Data Normalization (Adapter Pattern)** — Translates varying JSON payloads from different external providers into a unified, clean contract.
- **Pydantic Validation** — Strict response schema validation and type safety.
- **In-Memory Caching** — Simple TTL caching mechanism to respect external API rate limits and improve response latency.
- **Interactive API Documentation** — Built-in Swagger UI available out of the box (`/docs`).

---

## 🌍 Geographic Coverage

The gateway queries jobs by passing a `location` parameter through to each provider, so coverage depends on which countries Adzuna and Jooble support. Both providers have broad international reach, with strong coverage in Europe:

| Region | Example Locations | Adzuna | Jooble |
|---|---|:---:|:---:|
| DACH | Berlin, Munich, Hamburg, Vienna, Zurich | ✅ | ✅ |
| Central & Eastern Europe | Warsaw, Kraków, Prague, Budapest | ✅ | ✅ |
| Western Europe | London, Paris, Amsterdam, Brussels | ✅ | ✅ |
| Southern Europe | Madrid, Rome, Lisbon | ✅ | ✅ |
| Nordics | Stockholm, Copenhagen, Oslo | ✅ | ✅ |
| North America | US, Canada | ✅ | ✅ |
| Other | 60+ additional countries via Jooble | — | ✅ |

> ⚠️ Exact coverage is provider-dependent and can change without notice — always confirm against the current [Adzuna API docs](https://developer.adzuna.com/) and [Jooble API docs](https://jooble.org/api/about) before relying on a specific country/city combination in production.

---

## 🏗️ Architecture & Flow

The **Job Integration Gateway** acts as a stateless middleware layer designed around asynchronous execution, schema normalization, and resilient API handling.

```
┌─────────────────────────────────────────────────────────────────────┐
│                            CLIENT LAYER                              │
│           Frontend Web App / Postman / Swagger UI (/docs)            │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │  HTTP GET
                                    │  /api/v1/jobs?keyword=QA&location=Berlin
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          FASTAPI GATEWAY                             │
│                                                                       │
│  1. Request Handler & Query Validation (Pydantic)                    │
│  2. Cache Check Layer (TTL In-Memory Cache)                          │
│       ├── [ Cache Hit ]  ──▶ Return cached JSON immediately          │
│       └── [ Cache Miss ] ──▶ Proceed to Async Fetchers               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │   asyncio.gather() Orchestration │
                    ▼                                 ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│         ADZUNA CLIENT         │   │         JOOBLE CLIENT         │
│                                │   │                                │
│  • Protocol: HTTP GET         │   │  • Protocol: HTTP POST        │
│  • Query Params: app_id, key  │   │  • Body: JSON payload         │
│  • Async HTTP: httpx.AsyncClient│  │  • Async HTTP: httpx.AsyncClient│
└───────────────────────────────┘   └───────────────────────────────┘
                    │                                 │
                    │  Raw JSON Response               │  Raw JSON Response
                    ▼                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     NORMALIZER / ADAPTER LAYER                       │
│                                                                       │
│  • Maps provider-specific JSON schemas into a unified domain model   │
│  • Cleans raw text (removes HTML tags, formats currency strings)     │
│  • Handles fallback values for missing attributes (e.g., salary)     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AGGREGATION & DEDUPLICATION                       │
│                                                                       │
│  • Combines dataset streams into a single list                       │
│  • Deduplicates jobs based on unique URL / title + company hashing   │
│  • Updates TTL Cache entry                                           │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │  200 OK — Standardized JSON Response
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                            CLIENT LAYER                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🗺️ Development Roadmap

The full milestone-by-milestone development plan (setup, domain models, provider clients, adapters, aggregation, API, frontend, testing, deployment, and stretch goals) lives in a separate file to keep this README focused:

👉 **[ROADMAP.md](./ROADMAP.md)**

---

## 🧰 Tech Stack (Latest, as of Aug 2026)

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