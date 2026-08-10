import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY")


def fetch_jooble_jobs(keywords: str, location: str, limit: int = 5):
    if not JOOBLE_API_KEY:
        print("❌ [ERROR] JOOBLE_API_KEY is not set in .env")
        return

    url = f"https://jooble.org/api/{JOOBLE_API_KEY}"
    payload = {
        "keywords": keywords,
        "location": location,
        "page": "1",
        "resultOnPage": limit,
    }

    print(f"\n🚀 [GATEWAY] Requesting jobs from Jooble...")
    print(f"📍 Query: '{keywords}' | Location: '{location}'")

    start_time = time.time()

    try:
        response = requests.post(url, json=payload, timeout=10)
        elapsed = round((time.time() - start_time) * 1000, 2)
        response.raise_for_status()

        data = response.json()
        jobs = data.get("jobs", [])
        total = data.get("totalCount", 0)

        print(f"✅ [SUCCESS] Status: {response.status_code} OK ({elapsed} ms)")
        print(f"📊 Total jobs found: {total} | Showing top {len(jobs)}:\n")
        print("=" * 60)

        for idx, job in enumerate(jobs, start=1):
            salary = job.get("salary") or "Not specified"
            print(f"  {idx}. {job.get('title')}")
            print(f"     • Company:  {job.get('company')}")
            print(f"     • Location: {job.get('location')}")
            print(f"     • Salary:   {salary}")
            print(f"     • URL:      {job.get('link')}")
            print("-" * 60)

    except requests.exceptions.RequestException as e:
        print(f"❌ [ERROR] Gateway failed to fetch data: {e}")


if __name__ == "__main__":
    fetch_jooble_jobs(keywords="QA Automation", location="Berlin", limit=5)