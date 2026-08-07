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
