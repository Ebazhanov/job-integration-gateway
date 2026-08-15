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

US_STATE_CODES = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id", "il", "in", "ia",
    "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj",
    "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt",
    "va", "wa", "wv", "wi", "wy", "dc"
}


def is_title_relevant(title: str, query: str) -> bool:
    """Verifies if the job title matches any token from the user's search query."""
    if not query or not query.strip():
        return True

    tokens = [re.escape(token) for token in query.lower().split() if len(token) > 1]
    if not tokens:
        return True

    pattern = re.compile(r"\b(" + "|".join(tokens) + r")\b", re.IGNORECASE)
    return bool(pattern.search(title))


def is_location_relevant(job_location: str, target_location: str) -> bool:
    """Filters jobs matching European countries, US states (if target is US), or global Remote criteria."""
    if not target_location or not target_location.strip():
        return True

    job_loc = job_location.lower().strip()
    target_loc = target_location.lower().strip()

    if target_loc in job_loc:
        return True

    is_europe_target = target_loc in EUROPEAN_COUNTRIES or target_loc in EUROPEAN_CITIES or target_loc in ["europe", "eu"]
    if is_europe_target:
        if any(country in job_loc for country in EUROPEAN_COUNTRIES) or any(city in job_loc for city in EUROPEAN_CITIES):
            return True

    is_us_target = target_loc in ["us", "usa", "united states", "america"]
    if is_us_target:
        if any(term in job_loc for term in ["usa", "united states", "us"]):
            return True
        parts = [p.strip() for p in job_loc.split(",")]
        if len(parts) >= 2 and parts[-1] in US_STATE_CODES:
            return True

    remote_terms = ["remote", "worldwide", "anywhere", "work from home", "global", "cet"]
    if any(term in job_loc for term in remote_terms):
        if is_europe_target or not is_us_target:
            parts = [p.strip() for p in job_loc.split(",")]
            if len(parts) >= 2 and parts[-1] in US_STATE_CODES:
                return False
            if any(country in job_loc for country in ["united states", "usa", "us only", "india", "canada", "australia"]):
                return False
        return True

    return False


# --- Utility Endpoints ---
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["System"])
async def health_check():
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
            company_name = raw_job.get("company") or "Unknown Company"

            postings.append(
                JobPosting(
                    id=str(raw_job.get("id")) if raw_job.get("id") else None,
                    title=raw_job.get("title", "Untitled"),
                    company=company_name,
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
            company_name = raw_job.get("company_name") or raw_job.get("company") or "Unknown Company"

            postings.append(
                JobPosting(
                    id=f"remotive_{raw_job.get('id')}" if raw_job.get("id") else None,
                    title=raw_job.get("title", "Untitled"),
                    company=company_name,
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


async def fetch_jobicy_jobs(client: httpx.AsyncClient, tag: str = "", geo: str = "", fetch_depth: int = 50) -> List[JobPosting]:
    """Fetches remote job postings from Jobicy API v2 safely."""
    url = "https://jobicy.com/api/v2/remote-jobs"
    params = {"count": min(max(1, fetch_depth), 50)}

    clean_tag = tag.lower().strip() if tag else ""
    if clean_tag:
        params["tag"] = clean_tag

    clean_geo = geo.lower().strip() if geo else ""
    if clean_geo and clean_geo not in ["europe", "eu", "worldwide", "remote", "anywhere"]:
        params["geo"] = clean_geo

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/3.x",
        "Accept": "application/json",
    }

    try:
        response = await client.get(url, params=params, headers=headers, timeout=10.0)

        # Fallback if specific tag causes 400 Bad Request
        if response.status_code == 400 and "tag" in params:
            print(f"⚠️ [JOBICY WARN] Tag '{clean_tag}' rejected (400). Retrying without tag filter...")
            params.pop("tag", None)
            response = await client.get(url, params=params, headers=headers, timeout=10.0)

        response.raise_for_status()
        raw_data = response.json()
        raw_jobs = raw_data.get("jobs", [])
        print(f"🔹 [JOBICY RAW] Tag: '{params.get('tag', '')}' | Geo: '{params.get('geo', '')}' -> Got {len(raw_jobs)} raw jobs")

        postings = []
        for raw_job in raw_jobs:
            company_name = raw_job.get("companyName") or "Unknown Company"

            # Parse salary bounds cleanly
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
                    company=company_name,
                    location=raw_job.get("jobGeo") or "Worldwide / Remote",
                    salary=salary_str,
                    url=raw_job.get("url", ""),
                    source="Jobicy",
                )
            )
        return postings
    except httpx.HTTPStatusError as err:
        print(f"⚠️ [JOBICY HTTP {err.response.status_code}] Skipping query [{tag}]: {err}")
        return []
    except Exception as err:
        print(f"❌ [JOBICY ERROR] [{tag}] {err}")
        return []


# --- Aggregated Gateway Logic ---
async def aggregate_jobs(keywords: str = "QA Automation", location: str = "Europe", limit: int = 30) -> JobListResponse:
    """
    Concurrently fetches candidate pools from providers across specified search terms,
    applies relevance and location filtering, deduplicates, and returns clean results.
    """
    start_time = time.time()

    print(f"\n🚀 [GATEWAY] Aggregating jobs for Query: '{keywords}' | Location: '{location}'")

    async with httpx.AsyncClient() as client:
        remotive_results, jobicy_results, jooble_results = await asyncio.gather(
            # Remotive
            asyncio.gather(
                fetch_remotive_jobs(client, search_query=keywords, fetch_depth=50),
                return_exceptions=True
            ),
            # Jobicy
            asyncio.gather(
                fetch_jobicy_jobs(client, tag=keywords, geo=location, fetch_depth=50),
                return_exceptions=True
            ),
            # Jooble
            asyncio.gather(
                fetch_jooble_jobs(client, keywords=keywords, location=location, fetch_depth=50),
                return_exceptions=True
            ),
            return_exceptions=True
        )

    seen_identifiers = set()
    aggregated_postings: List[JobPosting] = []

    def process_batch(batch_results):
        if isinstance(batch_results, list):
            for res in batch_results:
                if isinstance(res, list):
                    for job in res:
                        dedup_key = f"{job.title.lower().strip()}_{job.company.lower().strip()}"
                        if dedup_key not in seen_identifiers:
                            if is_title_relevant(job.title, keywords) and is_location_relevant(job.location, location):
                                seen_identifiers.add(dedup_key)
                                aggregated_postings.append(job)

    # 1. Process Remotive results
    process_batch(remotive_results)

    # 2. Process Jobicy results
    process_batch(jobicy_results)

    # 3. Process Jooble results
    process_batch(jooble_results)

    # Slice results to respect the limit parameter
    final_results = aggregated_postings[:limit]

    elapsed = round((time.time() - start_time) * 1000, 2)
    print(f"✅ [SUCCESS] Returned {len(final_results)} relevant jobs (total matched: {len(aggregated_postings)}) in {elapsed} ms\n")

    return JobListResponse(
        total_count=len(aggregated_postings),
        count=len(final_results),
        results=final_results,
    )


# --- API Route ---
@app.get("/api/v1/jobs", response_model=JobListResponse, tags=["Jobs"])
async def get_jobs(
        keyword: str = Query("QA Automation", description="Job title or technology search query"),
        location: str = Query("Europe", description="City, country or region (e.g. Poland, Germany, Europe, USA)"),
        limit: int = Query(30, ge=1, le=50, description="Max results to return"),
):
    """Fetches real job postings aggregated from Jooble, Remotive & Jobicy."""
    return await aggregate_jobs(keywords=keyword, location=location, limit=limit)


if __name__ == "__main__":
    async def main():
        result = await aggregate_jobs(keywords="QA Automation", location="Europe", limit=30)

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