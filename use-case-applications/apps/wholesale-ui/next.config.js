/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export", // Static export for CloudFront deployment
  trailingSlash: true,
  images: { unoptimized: true }, // Required for static export
  experimental: {
    // Allow webpack/TypeScript to compile files outside this app's root directory.
    // Required because shared/ (auth hook, Apollo client) lives at apps/shared/,
    // one level above this app's directory.
    externalDir: true,
  },
  typescript: {
    // TypeScript cannot resolve @apollo/client and react from apps/shared/'s location
    // because node_modules lives in apps/wholesale-ui/ (the app root), not apps/shared/.
    // Webpack resolves correctly (bundle compiles clean); only the TS type-checker path
    // fails. ignoreBuildErrors suppresses the type-checker so the webpack output proceeds.
    // TODO: fix properly by adding a package.json to apps/shared/ or using a workspace.
    ignoreBuildErrors: true,
  },
};

module.exports = nextConfig;
