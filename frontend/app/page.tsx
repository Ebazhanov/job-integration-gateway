"use client";

import { useState, useEffect, useMemo } from "react";
import { fetchLiveJobs as fetchJobs } from "@/lib/api-client";
import { JobPosting } from "@/types/job";
import { JobCard } from "@/components/JobCard";

export default function HomePage() {
    const [keyword, setKeyword] = useState("QA Automation");
    const [location, setLocation] = useState("");
    const [jobs, setJobs] = useState<JobPosting[]>([]);
    const [loading, setLoading] = useState(true);
    const [statusMessage, setStatusMessage] = useState("Connecting to gateway...");
    const [totalCount, setTotalCount] = useState(0);

    const loadJobs = async (searchKw: string, searchLoc: string) => {
        setLoading(true);
        const locDisplay = searchLoc.trim() ? `in "${searchLoc}"` : "(Global / All locations)";
        setStatusMessage(`Aggregating jobs for "${searchKw}" ${locDisplay} across providers...`);

        try {
            const data = await fetchJobs({ keyword: searchKw, location: searchLoc });
            setJobs(data.results);
            setTotalCount(data.total_count);
            setStatusMessage(`Successfully loaded ${data.count} job postings.`);
        } catch (err) {
            console.error("Failed to load jobs:", err);
            setStatusMessage("Failed to connect to gateway. Showing cached / fallback results.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadJobs(keyword, location);
    }, []);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        loadJobs(keyword, location);
    };

    // Calculate job counts per provider source
    const sourceCounts = useMemo(() => {
        return jobs.reduce((acc, job) => {
            const src = job.source || "Other";
            acc[src] = (acc[src] || 0) + 1;
            return acc;
        }, {} as Record<string, number>);
    }, [jobs]);

    return (
        <main className="max-w-5xl mx-auto px-4 py-8">
            {/* Header */}
            <header className="mb-8 text-center sm:text-left">
                <h1 className="text-3xl font-extrabold tracking-tight text-gray-900 sm:text-4xl">
                    Multi-Source Job Aggregator
                </h1>
                <p className="mt-2 text-sm text-gray-600">
                    Aggregating live tech positions from <strong>Jooble</strong>, <strong>Remotive</strong>, and <strong>Jobicy</strong>
                    <span className="text-gray-400 font-normal"> (Arbeitnow integration coming soon)</span>.
                </p>
            </header>

            {/* Search Bar Form */}
            <form onSubmit={handleSearch} className="mb-8 flex flex-col sm:flex-row gap-3">
                <input
                    type="text"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    placeholder="Keyword (e.g. QA, Python, DevOps)"
                    className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                />
                <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="Location (e.g. Europe, Germany, Remote — leave blank for all)"
                    className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                />
                <button
                    type="submit"
                    disabled={loading}
                    className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm rounded-lg shadow-sm transition disabled:opacity-50 flex items-center justify-center gap-2"
                >
                    {loading && (
                        <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                    )}
                    {loading ? "Searching..." : "Search Jobs"}
                </button>
            </form>

            {/* Live Progress & Provider Source Summary */}
            <div className="mb-6 p-4 rounded-xl bg-gray-50 border border-gray-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                    <span className={`h-2.5 w-2.5 rounded-full ${loading ? "bg-amber-500 animate-ping" : "bg-emerald-500"}`} />
                    <span className="text-xs font-medium text-gray-700">{statusMessage}</span>
                </div>
                {!loading && (
                    <div className="flex flex-wrap items-center gap-2">
                        {Object.entries(sourceCounts).map(([sourceName, count]) => (
                            <span
                                key={sourceName}
                                className="text-xs font-medium px-2.5 py-1 bg-white text-gray-700 rounded-md border border-gray-200 shadow-2xs"
                            >
                                {sourceName}: <strong>{count}</strong>
                            </span>
                        ))}
                        <span className="text-xs font-semibold px-2.5 py-1 bg-blue-50 text-blue-700 rounded-md border border-blue-200">
                            {totalCount} Total
                        </span>
                    </div>
                )}
            </div>

            {/* Job Card Skeleton Loader & Grid */}
            {loading ? (
                <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2">
                    {[...Array(6)].map((_, i) => (
                        <div
                            key={`skeleton-${i}`}
                            className="p-5 border border-gray-200 rounded-xl shadow-sm bg-white animate-pulse flex flex-col justify-between space-y-4"
                        >
                            <div className="space-y-2">
                                <div className="h-5 bg-gray-200 rounded w-3/4" />
                                <div className="h-4 bg-gray-100 rounded w-1/2" />
                            </div>
                            <div className="flex justify-between items-center pt-4 border-t border-gray-100">
                                <div className="h-4 bg-gray-200 rounded w-1/3" />
                                <div className="h-8 bg-blue-100 rounded w-24" />
                            </div>
                        </div>
                    ))}
                </div>
            ) : jobs.length > 0 ? (
                <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2">
                    {jobs.map((job, idx) => (
                        <JobCard key={`${job.source}-${job.id || idx}-${job.url}`} job={job} />
                    ))}
                </div>
            ) : (
                <div className="text-center py-12 border-2 border-dashed border-gray-200 rounded-xl">
                    <p className="text-gray-500 text-sm">No job postings matched your criteria.</p>
                </div>
            )}
        </main>
    );
}