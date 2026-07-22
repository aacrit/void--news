import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

// Conditional basePath — defaults to /void--news for GitHub Pages.
// Cloudflare Pages and custom-domain deploys override via
// NEXT_PUBLIC_BASE_PATH="" in the deploy workflow env (root deploy).
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "/void--news";

// `output: "export"` (static export for GitHub / Cloudflare Pages) is applied
// for production builds only. Under `next dev` it is omitted so the IG render
// route (/ig/render/[postId]) can render arbitrary post IDs on demand for the
// Playwright capture step; with output:export the dev server 500s any dynamic
// param not pre-listed in generateStaticParams. Production export is unchanged.
export default function config(phase: string): NextConfig {
  const nextConfig: NextConfig = {
    basePath,
    trailingSlash: true,
    images: { unoptimized: true },
    compress: true,
    // Reduce bundle size by disabling source maps in production
    productionBrowserSourceMaps: false,
  };
  if (phase !== PHASE_DEVELOPMENT_SERVER) {
    nextConfig.output = "export";
  }
  return nextConfig;
}
