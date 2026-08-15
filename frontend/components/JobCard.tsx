import { JobPosting } from "@/types/job";

export function JobCard({ job }: { job: JobPosting }) {
    const getSourceBadgeColor = (source: string) => {
        switch (source.toLowerCase()) {
            case "jobicy":
                return "bg-purple-50 text-purple-700 border-purple-200";
            case "remotive":
                return "bg-emerald-50 text-emerald-700 border-emerald-200";
            case "jooble":
            default:
                return "bg-blue-50 text-blue-700 border-blue-200";
        }
    };

    const hasSalary =
        job.salary &&
        job.salary !== "Not specified" &&
        job.salary.trim() !== "";

    return (
        <div className="p-5 border border-gray-200 rounded-xl shadow-xs bg-white flex flex-col justify-between space-y-4 hover:border-gray-300 transition">
            <div>
                <div className="flex items-center justify-between gap-2 mb-2">
          <span
              className={`text-xs font-semibold px-2 py-0.5 rounded border ${getSourceBadgeColor(
                  job.source
              )}`}
          >
            {job.source || "Unknown"}
          </span>
                    <span
                        className="text-xs text-gray-500 font-medium truncate max-w-[200px]"
                        title={job.location}
                    >
            📍 {job.location}
          </span>
                </div>
                <h3 className="text-base font-bold text-gray-900 leading-snug">
                    {job.title}
                </h3>
                <p className="text-sm text-gray-600 mt-1 font-medium">{job.company}</p>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-gray-100">
        <span
            className={`text-xs font-medium px-2 py-1 rounded ${
                hasSalary
                    ? "bg-emerald-50 text-emerald-800 font-semibold border border-emerald-200"
                    : "text-gray-400"
            }`}
        >
          💳 {hasSalary ? job.salary : "Salary not disclosed"}
        </span>
                <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3.5 py-1.5 text-xs font-semibold bg-gray-900 hover:bg-gray-800 text-white rounded-lg transition"
                >
                    Apply &rarr;
                </a>
            </div>
        </div>
    );
}