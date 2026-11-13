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
    // Hide the Next.js dev-tools indicator. The IG slide capture runs against
    // `next dev`, and the indicator's bottom-left pill would render into the
    // 1080x1350 screenshot. Dev-only affordance; safe to disable.
    devIndicators: false,
    experimental: {
      // @phosphor-icons/react ships a barrel that does not tree-shake well —
      // importing a single icon can pull a large slice of the library into the
      // client bundle. optimizePackageImports rewrites named imports to direct
      // per-icon module paths, cutting the eager JS on every route that uses an
      // icon (NavBar, StoryCard, LeadStory, SkyboxBanner are all on the home
      // critical path). Lowers TBT and the JS the LCP estimate waits behind.
      optimizePackageImports: ["@phosphor-icons/react"],
    },
  };
  if (phase !== PHASE_DEVELOPMENT_SERVER) {
    nextConfig.output = "export";
  }
  return nextConfig;
}
