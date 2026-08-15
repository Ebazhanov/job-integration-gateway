export async function fetchLiveJobs({
                                        keyword = "QA Automation",
                                        location = "",
                                        limit = 30,
                                    }: {
    keyword?: string;
    location?: string;
    limit?: number;
}) {
    const params = new URLSearchParams({
        keyword,
        location,
        limit: limit.toString(),
    });

    const response = await fetch(`http://localhost:8000/api/v1/jobs?${params.toString()}`, {
        cache: "no-store",
    });

    if (!response.ok) {
        throw new Error(`Gateway returned status ${response.status}`);
    }

    return response.json();
}