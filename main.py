import os
import time
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

# Restrict CORS origins for security in production
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


# --- Root & Utility Routes ---
@app.get("/", include_in_schema=False)
async def root():
    """Redirects root visits directly to Swagger API docs."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["System"])
async def health_check():
    """System health check endpoint."""
    return {"status": "ok", "service": "job-integration-gateway"}


# --- Integration Logic ---
async def fetch_jooble_jobs(keywords: str, location: str, limit: int = 10) -> JobListResponse:
    """Asynchronously fetches, validates, and normalizes job postings from Jooble REST API."""
    if not JOOBLE_API_KEY:
        raise HTTPException(status_code=500, detail="JOOBLE_API_KEY is missing in environment.")

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

            job_postings = []
            for raw_job in raw_jobs:
                job = JobPosting(
                    id=str(raw_job.get("id")) if raw_job.get("id") else None,
                    title=raw_job.get("title", "Untitled"),
                    company=raw_job.get("company", "Unknown Company"),
                    location=raw_job.get("location", "Remote/Unspecified"),
                    salary=raw_job.get("salary") or "Not specified",
                    url=raw_job.get("link", ""),
                    source="Jooble",
                )
                job_postings.append(job)

            result = JobListResponse(
                total_count=total_count,
                count=len(job_postings),
                results=job_postings,
            )

            print(f"✅ [SUCCESS] Status: {response.status_code} OK ({elapsed} ms)")
            print(f"📊 Validated Jobs: {result.count} of {result.total_count} total\n")

            return result

    except httpx.TimeoutException:
        print("❌ [ERROR] Request timed out. Jooble API is taking too long to respond.")
        raise HTTPException(status_code=504, detail="Upstream provider timed out.")
    except httpx.HTTPStatusError as err:
        print(f"❌ [ERROR] HTTP error occurred: {err.response.status_code} - {err.response.text}")
        raise HTTPException(status_code=err.response.status_code, detail="Upstream API error.")
    except Exception as err:
        print(f"❌ [ERROR] Failed to fetch jobs: {str(err)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch jobs: {str(err)}")


# --- API Route ---
@app.get("/api/v1/jobs", response_model=JobListResponse, tags=["Jobs"])
async def get_jobs(
        keyword: str = Query("QA Automation", description="Job title or technology search query"),
        location: str = Query("Berlin", description="City or geographic region"),
        limit: int = Query(10, ge=1, le=50, description="Max results to return"),
):
    """Fetches real job postings from integrated upstream providers."""
    return await fetch_jooble_jobs(keywords=keyword, location=location, limit=limit)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)