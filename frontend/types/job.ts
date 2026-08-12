export interface JobPosting {
    id?: string | null;
    title: string;
    company: string;
    location: string;
    salary: string;
    url: string;
    source: 'Jooble' | 'Adzuna' | string;
}

export interface JobListResponse {
    total_count: number;
    count: number;
    results: JobPosting[];
}

export interface JobQuery {
    keyword: string;
    location: string;
    limit?: number;
}