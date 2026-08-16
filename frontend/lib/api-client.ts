import { JobPosting } from "@/types/job";

export interface FetchJobsParams {
    keyword?: string;
    location?: string;
    limit?: number;
}

export interface ApiResponse {
    count: number;
    total_count: number;
    results: JobPosting[];
}

// ============================================================================
// 1. Direct Client-Side Provider Fetchers (GitHub Pages / Fallback)
// ============================================================================

// --- REMOTIVE (with CORS Proxy & Query Normalization) ---
export async function fetchRemotiveJobs(keyword: string = "qa"): Promise<JobPosting[]> {
    const searchTerm = keyword.toLowerCase().includes("qa") ? "qa" : keyword;
    const targetUrl = `https://remotive.com/api/remote-jobs?search=${encodeURIComponent(searchTerm)}`;
    const proxyUrl = `https://corsproxy.io/?${encodeURIComponent(targetUrl)}`;

    try {
        const res = await fetch(proxyUrl);
        if (!res.ok) throw new Error(`Remotive HTTP status: ${res.status}`);

        const data = await res.json();
        const rawJobs = data.jobs || [];

        return rawJobs.map((job: any) => ({
            id: `remotive-${job.id}`,
            title: job.title || "Untitled Role",
            company: job.company_name || "Unknown Company",
            location: job.candidate_required_location || "Worldwide / Remote",
            salary: job.salary || "Not specified",
            url: job.url || "#",
            source: "Remotive",
        }));
    } catch (err) {
        console.error("⚠️ [REMOTIVE FETCH ERROR]:", err);
        return [];
    }
}

// --- JOBICY (with CORS Proxy) ---
export async function fetchJobicyJobs(keyword: string = "qa", location: string = ""): Promise<JobPosting[]> {
    let geoParam = "";
    const locLower = location.toLowerCase();

    if (locLower.includes("usa") || locLower.includes("us")) geoParam = "usa";
    else if (locLower.includes("canada")) geoParam = "canada";
    else if (locLower.includes("uk") || locLower.includes("kingdom")) geoParam = "uk";
    else if (locLower.includes("europe") || locLower.includes("eu")) geoParam = "emea";

    const targetUrl = `https://jobicy.com/api/v2/remote-jobs?count=50${geoParam ? `&geo=${geoParam}` : ""}`;
    const proxyUrl = `https://corsproxy.io/?${encodeURIComponent(targetUrl)}`;

    try {
        const res = await fetch(proxyUrl);
        if (!res.ok) throw new Error(`Jobicy HTTP status: ${res.status}`);

        const data = await res.json();
        const rawJobs = data.jobs || [];

        return rawJobs.map((job: any) => {
            const salaryMin = job.annualSalaryMin;
            const salaryMax = job.annualSalaryMax;
            const currency = job.salaryCurrency || "USD";

            let salaryStr = "Not specified";
            if (salaryMin || salaryMax) {
                salaryStr = `${currency} ${salaryMin || ""} - ${salaryMax || ""}`.trim();
            }

            return {
                id: `jobicy-${job.id}`,
                title: job.jobTitle || "Untitled Role",
                company: job.companyName || "Unknown Company",
                location: job.jobGeo || job.jobCountry || "Worldwide / Remote",
                salary: salaryStr,
                url: job.url || "#",
                source: "Jobicy",
            };
        });
    } catch (err) {
        console.error("⚠️ [JOBICY FETCH ERROR]:", err);
        return [];
    }
}

// ============================================================================
// 2. Gateway API & Hybrid Execution
// ============================================================================

export async function fetchLiveJobs({
                                        keyword = "QA Automation",
                                        location = "",
                                        limit = 30,
                                    }: FetchJobsParams = {}): Promise<ApiResponse> {
    const params = new URLSearchParams({
        keyword,
        location,
        limit: limit.toString(),
    });

    const gatewayUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
        // Attempt local FastAPI backend gateway
        const response = await fetch(`${gatewayUrl}/api/v1/jobs?${params.toString()}`, {
            cache: "no-store",
        });

        if (response.ok) {
            return await response.json();
        }
    } catch {
        console.warn("⚠️ Gateway unreachable. Falling back to direct client-side provider fetchers.");
    }

    // Fallback for static GitHub Pages client-side aggregation across Remotive & Jobicy
    const [remotiveJobs, jobicyJobs] = await Promise.all([
        fetchRemotiveJobs(keyword),
        fetchJobicyJobs(keyword, location),
    ]);

    const allJobs = [...remotiveJobs, ...jobicyJobs];

    // Filtering for QA relevance & target location
    const qaRegex = /\b(qa|sdet|quality assurance|test|testing|automation)\b/i;
    const filtered = allJobs.filter((job) => {
        const titleMatch = qaRegex.test(job.title);
        if (!titleMatch) return false;

        if (!location) return true;
        const locLower = location.toLowerCase();
        const jobLoc = job.location.toLowerCase();

        return (
            jobLoc.includes(locLower) ||
            jobLoc.includes("remote") ||
            jobLoc.includes("worldwide") ||
            jobLoc.includes("emea")
        );
    });

    return {
        count: Math.min(filtered.length, limit),
        total_count: filtered.length,
        results: filtered.slice(0, limit),
    };
}