import { JobListResponse, JobQuery } from '../types/job';

const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || 'https://job-integration-gateway.onrender.com';

export async function fetchLiveJobs(query: JobQuery): Promise<JobListResponse> {
    const params = new URLSearchParams({
        keyword: query.keyword,
        location: query.location,
        limit: String(query.limit || 10),
    });

    const response = await fetch(`${API_BASE_URL}/api/v1/jobs?${params.toString()}`);

    if (!response.ok) {
        throw new Error(`Failed to fetch jobs: ${response.statusText}`);
    }

    return response.json();
}