import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  basePath: "/void--news",
  images: { unoptimized: true },
};

export default nextConfig;
