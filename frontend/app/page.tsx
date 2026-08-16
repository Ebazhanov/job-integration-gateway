"use client";

import { useState, useEffect } from "react";
import { fetchLiveJobs as fetchJobs } from "@/lib/api-client";
import { JobPosting } from "@/types/job";
import { JobCard } from "@/components/JobCard";

export default function HomePage() {
    const [keyword, setKeyword] = useState("QA Automation");
    const [location, setLocation] = useState("");
    const [providerFilter, setProviderFilter] = useState("all");
    const [jobs, setJobs] = useState<JobPosting[]>([]);
    const [loading, setLoading] = useState(true);
    const [statusMessage, setStatusMessage] = useState("Connecting to gateway...");
    const [totalCount, setTotalCount] = useState(0);

    const loadJobs = async (searchKw: string, searchLoc: string) => {
        setLoading(true);
        setStatusMessage(`Aggregating jobs for "${searchKw}" across providers...`);

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

    const displayedJobs = jobs.filter((job) =>
        providerFilter === "all" ? true : job.source.toLowerCase() === providerFilter.toLowerCase()
    );

    // Compute breakdown by provider source
    const providerCounts = jobs.reduce((acc, job) => {
        const src = job.source || "Other";
        acc[src] = (acc[src] || 0) + 1;
        return acc;
    }, {} as Record<string, number>);

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
                    placeholder="Keyword (e.g. QA, SDET)"
                    className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                />
                <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="Location (e.g. Europe, Germany, Remote — leave blank for all)"
                    className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                />
                <select
                    value={providerFilter}
                    onChange={(e) => setProviderFilter(e.target.value)}
                    className="px-4 py-2.5 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white"
                >
                    <option value="all">All Providers</option>
                    <option value="jobicy">Jobicy</option>
                    <option value="jooble">Jooble</option>
                    <option value="remotive">Remotive</option>
                </select>
                <button
                    type="submit"
                    disabled={loading}
                    className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm rounded-lg shadow-sm transition disabled:opacity-50 flex items-center justify-center gap-2"
                >
                    {loading ? "Searching..." : "Search Jobs"}
                </button>
            </form>

            {/* Progress & Provider Breakdown Banner */}
            <div className="mb-6 p-4 rounded-xl bg-gray-50 border border-gray-200 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                    <span className={`h-2.5 w-2.5 rounded-full ${loading ? "bg-amber-500 animate-ping" : "bg-emerald-500"}`} />
                    <span className="text-xs font-medium text-gray-700">{statusMessage}</span>
                </div>

                {!loading && (
                    <div className="flex items-center gap-2 flex-wrap">
                        {["Jobicy", "Jooble", "Remotive"].map((provider) => (
                            <span
                                key={provider}
                                className="text-xs font-medium px-2.5 py-1 bg-white border border-gray-200 rounded-lg text-gray-700 shadow-2xs"
                            >
                {provider}: <strong className="text-gray-900">{providerCounts[provider] || 0}</strong>
              </span>
                        ))}
                        <span className="text-xs font-bold px-3 py-1 bg-blue-50 text-blue-700 rounded-lg border border-blue-200">
              {totalCount} Total
            </span>
                    </div>
                )}
            </div>

            {/* Job Card Grid */}
            {loading ? (
                <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2">
                    {[...Array(6)].map((_, i) => (
                        <div key={i} className="p-5 border border-gray-200 rounded-xl shadow-sm bg-white animate-pulse h-40" />
                    ))}
                </div>
            ) : displayedJobs.length > 0 ? (
                <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2">
                    {displayedJobs.map((job) => (
                        <JobCard key={job.id || job.url} job={job} />
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