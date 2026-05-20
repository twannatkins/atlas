/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export", // Static export for CloudFront deployment
  trailingSlash: true,
  images: { unoptimized: true }, // Required for static export
};

module.exports = nextConfig;
