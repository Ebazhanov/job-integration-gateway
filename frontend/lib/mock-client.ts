import { JobPosting, JobListResponse, JobQuery } from '../../frontend/types/job';

const MOCK_JOBS: JobPosting[] = [
    {
        id: "1",
        title: "Senior QA Automation Engineer",
        company: "beyonnex.io",
        location: "Berlin, Germany",
        salary: "Not specified",
        url: "https://example.com/job/1",
        source: "Jooble",
    },
    {
        id: "2",
        title: "Test Automation Engineer (Playwright / TypeScript)",
        company: "Tech Berlin GmbH",
        location: "Berlin, Germany",
        salary: "€75,000 - €85,000",
        url: "https://example.com/job/2",
        source: "Adzuna",
    },
];

export async function fetchMockJobs(query: JobQuery): Promise<JobListResponse> {
    // Simulate network latency
    await new Promise((resolve) => setTimeout(resolve, 300));

    const filtered = MOCK_JOBS.filter(
        (job) =>
            job.title.toLowerCase().includes(query.keyword.toLowerCase()) ||
            job.location.toLowerCase().includes(query.location.toLowerCase())
    );

    return {
        total_count: filtered.length,
        count: filtered.length,
        results: filtered,
    };
}