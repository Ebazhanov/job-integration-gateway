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


# --- Relevance & Location Filters ---
EUROPEAN_COUNTRIES = {
    "europe", "eu", "germany", "deutschland", "poland", "polska", "france", "spain",
    "italy", "netherlands", "holland", "belgium", "switzerland", "austria", "portugal",
    "sweden", "norway", "finland", "denmark", "ireland", "uk", "united kingdom",
    "czech republic", "czechia", "slovakia", "hungary", "romania", "bulgaria",
    "greece", "croatia", "serbia", "slovenia", "estonia", "latvia", "lithuania",
    "ukraine", "belarus", "moldova", "cyprus", "malta", "iceland", "luxembourg"
}

EUROPEAN_CITIES = {
    "berlin", "munich", "münchen", "hamburg", "frankfurt", "warsaw", "warszawa",
    "krakow", "kraków", "wroclaw", "wrocław", "gdansk", "gdańsk", "poznan", "poznań",
    "paris", "madrid", "barcelona", "amsterdam", "brussels", "vienna", "wien",
    "zurich", "zürich", "lisbon", "stockholm", "oslo", "helsinki", "copenhagen",
    "dublin", "london", "prague", "bratislava", "budapest", "bucharest", "tallinn", "riga", "vilnius"
}


def is_title_relevant(title: str, query: str) -> bool:
    """Verifies if the job title matches the search query or core domain tokens."""
    if not query or not query.strip():
        return True

    title_lower = title.lower()

    # Search query token matching
    tokens = [re.escape(t) for t in query.lower().split() if len(t) > 1]
    qa_tokens = ["qa", "sdet", "test", "tester", "testing", "quality"]

    pattern = re.compile(r"\b(" + "|".join(set(tokens + qa_tokens)) + r")\b", re.IGNORECASE)
    return bool(pattern.search(title_lower))


def is_location_relevant(job_location: str, target_location: str) -> bool:
    """Passes all postings if no target location specified; otherwise applies region filtering."""
    if not target_location or not target_location.strip():
        return True

    job_loc = job_location.lower().strip()
    target_loc = target_location.lower().strip()

    # Direct match or global remote
    if target_loc in job_loc or any(term in job_loc for term in ["remote", "worldwide", "anywhere", "global"]):
        return True

    is_europe_target = target_loc in EUROPEAN_COUNTRIES or target_loc in EUROPEAN_CITIES or target_loc in ["europe", "eu"]
    if is_europe_target:
        if any(country in job_loc for country in EUROPEAN_COUNTRIES) or any(city in job_loc for city in EUROPEAN_CITIES):
            return True

    return False


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
                    company=raw_job.get("company") or "Unknown Company",
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


async def fetch_remotive_jobs(client: httpx.AsyncClient, search_query: str = "", fetch_depth: int = 100) -> List[JobPosting]:
    """Fetches remote job postings from Remotive API."""
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
                    id=f"remotive_{raw_job.get('id')}" if raw_job.get("id") else None,
                    title=raw_job.get("title", "Untitled"),
                    company=raw_job.get("company_name") or "Unknown Company",
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


async def fetch_jobicy_jobs(client: httpx.AsyncClient, tag: str = "", fetch_depth: int = 50) -> List[JobPosting]:
    """Fetches remote job postings from Jobicy API v2 safely."""
    url = "https://jobicy.com/api/v2/remote-jobs"
    params = {"count": min(max(1, fetch_depth), 50)}

    clean_tag = tag.lower().strip() if tag else ""
    if clean_tag:
        params["tag"] = clean_tag

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/3.x",
        "Accept": "application/json",
    }

    try:
        response = await client.get(url, params=params, headers=headers, timeout=10.0)

        # Fallback if tag parameter causes 400 Bad Request
        if response.status_code == 400 and "tag" in params:
            print(f"⚠️ [JOBICY WARN] Tag '{clean_tag}' rejected (400). Retrying without tag filter...")
            params.pop("tag", None)
            response = await client.get(url, params=params, headers=headers, timeout=10.0)

        response.raise_for_status()
        raw_data = response.json()
        raw_jobs = raw_data.get("jobs", [])
        print(f"🔹 [JOBICY RAW] Tag: '{params.get('tag', '')}' -> Got {len(raw_jobs)} raw jobs")

        postings = []
        for raw_job in raw_jobs:
            salary_min = raw_job.get("annualSalaryMin")
            salary_max = raw_job.get("annualSalaryMax")
            currency = raw_job.get("salaryCurrency", "").strip()

            if salary_min and salary_max:
                salary_str = f"{salary_min} - {salary_max} {currency}".strip()
            elif salary_min:
                salary_str = f"From {salary_min} {currency}".strip()
            elif salary_max:
                salary_str = f"Up to {salary_max} {currency}".strip()
            else:
                salary_str = "Not specified"

            postings.append(
                JobPosting(
                    id=f"jobicy_{raw_job.get('id')}" if raw_job.get("id") else None,
                    title=raw_job.get("jobTitle", "Untitled"),
                    company=raw_job.get("companyName") or "Unknown Company",
                    location=raw_job.get("jobGeo") or "Worldwide / Remote",
                    salary=salary_str,
                    url=raw_job.get("url", ""),
                    source="Jobicy",
                )
            )
        return postings
    except Exception as err:
        print(f"❌ [JOBICY ERROR] [{tag}] {err}")
        return []


# --- Aggregated Gateway Logic ---
async def aggregate_jobs(keywords: str = "QA Automation", location: str = "", limit: int = 30) -> JobListResponse:
    start_time = time.time()
    print(f"\n🚀 [GATEWAY] Aggregating jobs for Query: '{keywords}' | Location: '{location}'")

    async with httpx.AsyncClient() as client:
        # CONCURRENT FETCH FROM ALL THREE PROVIDERS
        remotive_batch, jobicy_batch, jooble_batch = await asyncio.gather(
            asyncio.gather(
                fetch_remotive_jobs(client, search_query="qa", fetch_depth=50),
                fetch_remotive_jobs(client, search_query="testing", fetch_depth=50),
                return_exceptions=True
            ),
            asyncio.gather(
                fetch_jobicy_jobs(client, tag="qa", fetch_depth=50),
                fetch_jobicy_jobs(client, tag="testing", fetch_depth=50),
                fetch_jobicy_jobs(client, tag="dev", fetch_depth=50),
                return_exceptions=True
            ),
            asyncio.gather(
                fetch_jooble_jobs(client, keywords, location=location, fetch_depth=50),
                fetch_jooble_jobs(client, "QA Automation", location=location, fetch_depth=50),
                return_exceptions=True
            ),
            return_exceptions=True
        )

    seen_identifiers = set()
    aggregated_postings: List[JobPosting] = []

    def process_batch(batch):
        if isinstance(batch, list):
            for res in batch:
                if isinstance(res, list):
                    for job in res:
                        dedup_key = f"{job.title.lower().strip()}_{job.company.lower().strip()}"
                        if dedup_key not in seen_identifiers:
                            if is_title_relevant(job.title, keywords) and is_location_relevant(job.location, location):
                                seen_identifiers.add(dedup_key)
                                aggregated_postings.append(job)

    # Process all batch streams
    process_batch(remotive_batch)
    process_batch(jobicy_batch)
    process_batch(jooble_batch)

    final_results = aggregated_postings[:limit]
    elapsed = round((time.time() - start_time) * 1000, 2)
    print(f"✅ [SUCCESS] Returned {len(final_results)} relevant jobs (total matched: {len(aggregated_postings)}) in {elapsed} ms\n")

    return JobListResponse(
        total_count=len(aggregated_postings),
        count=len(final_results),
        results=final_results,
    )


# --- API Endpoints ---
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "job-integration-gateway"}


@app.get("/api/v1/jobs", response_model=JobListResponse, tags=["Jobs"])
async def get_jobs(
        keyword: str = Query("QA Automation", description="Job title or technology search query"),
        location: str = Query("", description="City, country or region (leave empty for all locations)"),
        limit: int = Query(30, ge=1, le=50, description="Max results to return"),
):
    return await aggregate_jobs(keywords=keyword, location=location, limit=limit)


if __name__ == "__main__":
    async def main():
        result = await aggregate_jobs(keywords="QA Automation", location="", limit=30)

        print("=" * 60)
        print(f"📊 Total Relevant Jobs Fetched ({result.count} of {result.total_count}):")
        print("=" * 60 + "\n")

        for idx, job in enumerate(result.results, start=1):
            print(f"{idx}. [{job.source}] {job.title}")
            print(f"   • Company:  {job.company}")
            print(f"   • Location: {job.location}")
            print(f"   • Salary:   {job.salary}")
            print(f"   • URL:      {job.url}")
            print("-" * 60)

    asyncio.run(main())