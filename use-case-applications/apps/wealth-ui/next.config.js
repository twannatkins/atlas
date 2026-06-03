/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  experimental: {
    // Allow webpack/TypeScript to compile files outside this app's root directory.
    // Required for apps/shared/ (auth hook, Apollo client).
    externalDir: true,
  },
  typescript: {
    // Same cross-directory TS resolution issue as wholesale-ui. See that file for details.
    // TODO: fix properly via apps/shared/package.json or workspace setup.
    ignoreBuildErrors: true,
  },
};

module.exports = nextConfig;
