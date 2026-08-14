import os
import re
import time
import asyncio
import httpx
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, List

load_dotenv()

JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY")

app = FastAPI(title="Job Integration Gateway API", version="1.0.0")

# Restrict CORS origins for production security
allowed_origins = [
    "http://localhost:3000",
    "https://ebazhanov.github.io",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Domain Models ---
class JobPosting(BaseModel):
    id: Optional[str] = Field(default=None, description="Unique job identifier")
    title: str
    company: str
    location: str
    salary: str = "Not specified"
    url: str
    source: str = "Jooble"


class JobListResponse(BaseModel):
    total_count: int
    count: int
    results: List[JobPosting]


# --- Relevance Filter ---
QA_TITLE_PATTERN = re.compile(
    r"\b(qa|sdet|test|tester|testing|softwaretester|quality assurance|quality engineer|quality manager)\b",
    re.IGNORECASE
)

def is_qa_relevant(title: str) -> bool:
    """Accurately verifies if a job title belongs to the QA/Testing domain."""
    title_lower = title.lower()

    # Exclude IT/DevOps/Infrastructure automation engineers unless explicitly tagged with QA/Test/Quality
    if "automation engineer" in title_lower and not any(k in title_lower for k in ["qa", "test", "quality", "sdet"]):
        return False

    return bool(QA_TITLE_PATTERN.search(title_lower))


# --- Utility Endpoints ---
@app.get("/", include_in_schema=False)
async def root():
    """Redirects root visits directly to Swagger API docs."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["System"])
async def health_check():
    """System health check endpoint."""
    return {"status": "ok", "service": "job-integration-gateway"}


# --- Upstream Integration Clients ---
async def fetch_jooble_jobs(client: httpx.AsyncClient, keywords: str, location: str = "", fetch_depth: int = 50) -> List[JobPosting]:
    """Fetches job postings from Jooble API."""
    if not JOOBLE_API_KEY:
        print("⚠️ [JOOBLE] JOOBLE_API_KEY missing. Skipping Jooble fetch.")
        return []

    url = f"https://jooble.org/api/{JOOBLE_API_KEY}"
    payload = {
        "keywords": keywords,
        "location": location,
        "page": "1",
        "resultOnPage": fetch_depth,
    }

    try:
        response = await client.post(url, json=payload, timeout=10.0)
        response.raise_for_status()
        raw_data = response.json()
        raw_jobs = raw_data.get("jobs", [])
        print(f"🔹 [JOOBLE RAW] Query: '{keywords}' | Loc: '{location}' -> Got {len(raw_jobs)} raw jobs")

        postings = []
        for raw_job in raw_jobs:
            postings.append(
                JobPosting(
                    id=str(raw_job.get("id")) if raw_job.get("id") else None,
                    title=raw_job.get("title", "Untitled"),
                    company=raw_job.get("company", "Unknown Company"),
                    location=raw_job.get("location", "Remote/Unspecified"),
                    salary=raw_job.get("salary") or "Not specified",
                    url=raw_job.get("link", ""),
                    source="Jooble",
                )
            )
        return postings
    except Exception as err:
        print(f"❌ [JOOBLE ERROR] [{keywords}] {err}")
        return []


async def fetch_remotive_jobs(client: httpx.AsyncClient, search_query: str = "qa", fetch_depth: int = 50) -> List[JobPosting]:
    """Fetches remote job postings from Remotive API using valid search parameters."""
    url = f"https://remotive.com/api/remote-jobs?search={search_query}"

    try:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        raw_data = response.json()
        raw_jobs = raw_data.get("jobs", [])
        print(f"🔹 [REMOTIVE RAW] Search: '{search_query}' -> Got {len(raw_jobs)} raw jobs")

        postings = []
        for raw_job in raw_jobs[:fetch_depth]:
            postings.append(
                JobPosting(
                    id=str(raw_job.get("id")) if raw_job.get("id") else None,
                    title=raw_job.get("title", "Untitled"),
                    company=raw_job.get("company_name", "Unknown Company"),
                    location=raw_job.get("candidate_required_location") or "Worldwide / Remote",
                    salary=raw_job.get("salary") or "Not specified",
                    url=raw_job.get("url", ""),
                    source="Remotive",
                )
            )
        return postings
    except Exception as err:
        print(f"❌ [REMOTIVE ERROR] [{search_query}] {err}")
        return []


# --- Aggregated Gateway Logic ---
async def aggregate_jobs(keywords: str = "QA Automation", location: str = "Germany", limit: int = 20) -> JobListResponse:
    """
    Concurrently fetches candidate pools from providers, applies strict domain
    relevance filtering, deduplicates, and returns clean results.
    """
    start_time = time.time()

    print(f"\n🚀 [GATEWAY] Aggregating jobs for Query: '{keywords}' | Location: '{location}'")

    async with httpx.AsyncClient() as client:
        # Query Jooble with empty location & specified location + Query Remotive with valid search strings
        tasks = [
            fetch_jooble_jobs(client, keywords, location=location, fetch_depth=50),
            fetch_jooble_jobs(client, "QA Automation", location="", fetch_depth=50),
            fetch_jooble_jobs(client, "Software Test", location="", fetch_depth=50),
            fetch_remotive_jobs(client, search_query="qa", fetch_depth=50),
            fetch_remotive_jobs(client, search_query="testing", fetch_depth=50),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Deduplicate and filter by strict domain relevance
    seen_identifiers = set()
    aggregated_postings: List[JobPosting] = []

    for res in results:
        if isinstance(res, list):
            for job in res:
                identifier = job.id if job.id else job.url
                if identifier and identifier not in seen_identifiers:
                    if is_qa_relevant(job.title):
                        seen_identifiers.add(identifier)
                        aggregated_postings.append(job)

    elapsed = round((time.time() - start_time) * 1000, 2)
    print(f"✅ [SUCCESS] Returned {len(aggregated_postings)} strict QA/Testing jobs ({elapsed} ms)\n")

    return JobListResponse(
        total_count=len(aggregated_postings),
        count=len(aggregated_postings),
        results=aggregated_postings,
    )


# --- API Route ---
@app.get("/api/v1/jobs", response_model=JobListResponse, tags=["Jobs"])
async def get_jobs(
        keyword: str = Query("QA Automation", description="Job title or technology search query"),
        location: str = Query("Germany", description="City or country (e.g. Germany, Berlin)"),
        limit: int = Query(20, ge=1, le=50, description="Max results to return"),
):
    """Fetches real job postings aggregated from Jooble & Remotive."""
    return await aggregate_jobs(keywords=keyword, location=location, limit=limit)


if __name__ == "__main__":
    async def main():
        result = await aggregate_jobs(keywords="QA Automation", location="Germany", limit=20)

        print("=" * 60)
        print(f"📊 Total Relevant QA/Testing Jobs Fetched ({result.count}):")
        print("=" * 60 + "\n")

        for idx, job in enumerate(result.results, start=1):
            print(f"{idx}. [{job.source}] {job.title}")
            print(f"   • Company:  {job.company}")
            print(f"   • Location: {job.location}")
            print(f"   • Salary:   {job.salary}")
            print(f"   • URL:      {job.url}")
            print("-" * 60)

    asyncio.run(main())