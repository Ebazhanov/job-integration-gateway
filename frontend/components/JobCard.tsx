import React from 'react';
import { JobPosting } from '../../frontend/types/job';

interface JobCardProps {
    job: JobPosting;
}

export const JobCard: React.FC<JobCardProps> = ({ job }) => {
    return (
        <div className="border border-gray-200 rounded-lg p-5 shadow-sm hover:shadow-md transition-shadow bg-white flex flex-col justify-between">
            <div>
                <div className="flex justify-between items-start mb-2">
                    <h3 className="text-lg font-semibold text-gray-900 line-clamp-1">
                        {job.title}
                    </h3>
                    <span className="inline-block px-2.5 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
            {job.source}
          </span>
                </div>
                <p className="text-sm font-medium text-gray-700 mb-1">{job.company}</p>
                <p className="text-xs text-gray-500 mb-3">📍 {job.location}</p>
            </div>

            <div className="pt-3 border-t border-gray-100 flex items-center justify-between mt-2">
        <span className="text-xs font-semibold text-gray-700">
          💰 {job.salary}
        </span>
                <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1"
                >
                    View Job &rarr;
                </a>
            </div>
        </div>
    );
};