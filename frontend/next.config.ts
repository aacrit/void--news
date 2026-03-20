import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  basePath: "/void--news",
  images: { unoptimized: true },
  compress: true,
  // Reduce bundle size by disabling source maps in production
  productionBrowserSourceMaps: false,
};

export default nextConfig;
