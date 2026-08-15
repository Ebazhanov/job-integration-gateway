import type { NextConfig } from "next";

const isGithubActions = process.env.GITHUB_ACTIONS === "true";

const repoName = process.env.GITHUB_REPOSITORY
  ? process.env.GITHUB_REPOSITORY.split("/")[1]
  : "";

const nextConfig: NextConfig = {
  output: "export",
  basePath: isGithubActions && repoName ? `/${repoName}` : "",
  assetPrefix: isGithubActions && repoName ? `/${repoName}/` : "",
  images: {
    unoptimized: true,
  },
};

export default nextConfig;