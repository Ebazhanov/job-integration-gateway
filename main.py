import os
import time
import asyncio
import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, List

load_dotenv()

JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY")


# --- Domain Models (Unified Contract) ---
class JobPosting(BaseModel):
    """Unified schema contract for job postings across all providers."""
    id: Optional[str] = Field(default=None, description="Unique job identifier")
    title: str
    company: str
    location: str
    salary: str = "Not specified"
    url: str
    source: str = "Jooble"


class JobListResponse(BaseModel):
    """Standardized response model served to clients."""
    total_count: int
    count: int
    results: List[JobPosting]


# --- Integration Logic (Async) ---
async def fetch_jooble_jobs(keywords: str, location: str, limit: int = 5) -> Optional[JobListResponse]:
    """Asynchronously fetches, validates, and normalizes job postings from Jooble REST API."""
    if not JOOBLE_API_KEY:
        print("❌ [ERROR] JOOBLE_API_KEY is not set in .env")
        return None

    url = f"https://jooble.org/api/{JOOBLE_API_KEY}"
    payload = {
        "keywords": keywords,
        "location": location,
        "page": "1",
        "resultOnPage": limit,
    }

    print(f"\n🚀 [GATEWAY] Requesting jobs from Jooble (Async)...")
    print(f"📍 Query: '{keywords}' | Location: '{location}'")

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            elapsed = round((time.time() - start_time) * 1000, 2)
            response.raise_for_status()

            raw_data = response.json()
            raw_jobs = raw_data.get("jobs", [])
            total_count = raw_data.get("totalCount", 0)

            # Mapping raw payload to Pydantic domain models
            job_postings = []
            for raw_job in raw_jobs:
                job = JobPosting(
                    id=str(raw_job.get("id")) if raw_job.get("id") else None,
                    title=raw_job.get("title", "Untitled"),
                    company=raw_job.get("company", "Unknown Company"),
                    location=raw_job.get("location", "Remote/Unspecified"),
                    salary=raw_job.get("salary") or "Not specified",
                    url=raw_job.get("link", ""),
                    source="Jooble"
                )
                job_postings.append(job)

            result = JobListResponse(
                total_count=total_count,
                count=len(job_postings),
                results=job_postings
            )

            print(f"✅ [SUCCESS] Status: {response.status_code} OK ({elapsed} ms)")
            print(f"📊 Validated Jobs: {result.count} of {result.total_count} total\n")
            print("=" * 60)

            for idx, job in enumerate(result.results, start=1):
                print(f"  {idx}. {job.title}")
                print(f"     • Company:  {job.company}")
                print(f"     • Location: {job.location}")
                print(f"     • Salary:   {job.salary}")
                print(f"     • URL:      {job.url}")
                print("-" * 60)

            return result

    except httpx.TimeoutException:
        print("❌ [ERROR] Request timed out. Jooble API is taking too long to respond.")
    except httpx.HTTPStatusError as err:
        print(f"❌ [ERROR] HTTP error occurred: {err.response.status_code} - {err.response.text}")
    except httpx.RequestError as err:
        print(f"❌ [ERROR] Network communication error: {err}")
    except Exception as err:
        print(f"❌ [ERROR] Validation or parsing failed: {err}")

    return None


if __name__ == "__main__":
    asyncio.run(fetch_jooble_jobs(keywords="QA Automation", location="Berlin", limit=5))