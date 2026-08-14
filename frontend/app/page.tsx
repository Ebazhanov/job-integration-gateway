'use client';

import { useEffect, useState } from 'react';
import { JobCard } from '../components/JobCard';
import { fetchLiveJobs } from '../lib/api-client';
import { JobPosting } from '../types/job';

export default function HomePage() {
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLiveJobs({ keyword: 'QA Automation', location: 'Berlin' })
        .then((res) => {
          setJobs(res.results);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message);
          setLoading(false);
        });
  }, []);

  return (
      <main className="min-h-screen bg-gray-50 py-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold text-gray-900 mb-6">
                Job Integration Gateway
            </h1>

          {loading && <p className="text-gray-500">Loading live jobs...</p>}
          {error && <p className="text-red-500">Error: {error}</p>}

          {!loading && !error && (
              <div className="grid gap-4 md:grid-cols-2">
                {jobs.map((job, idx) => (
                    <JobCard key={job.id || idx} job={job} />
                ))}
              </div>
          )}
        </div>
      </main>
  );
}