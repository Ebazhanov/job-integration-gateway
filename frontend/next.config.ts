import type { NextConfig } from 'next';

const isGithubActions = process.env.GITHUB_ACTIONS || false;

const nextConfig: NextConfig = {
    output: 'export',
    images: {
        unoptimized: true,
    },
    basePath: isGithubActions ? '/job-integration-gateway' : '',
    assetPrefix: isGithubActions ? '/job-integration-gateway/' : '',
};

export default nextConfig;