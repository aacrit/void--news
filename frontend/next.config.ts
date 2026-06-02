import type { NextConfig } from "next";

// Conditional basePath — defaults to /void--news for GitHub Pages.
// Cloudflare Pages and custom-domain deploys override via
// NEXT_PUBLIC_BASE_PATH="" in the deploy workflow env (root deploy).
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "/void--news";

const nextConfig: NextConfig = {
  output: "export",
  basePath,
  trailingSlash: true,
  images: { unoptimized: true },
  compress: true,
  // Reduce bundle size by disabling source maps in production
  productionBrowserSourceMaps: false,
};

export default nextConfig;
