import type { MetadataRoute } from "next";
import { SITE_URL } from "./lib/siteMeta";

/* Static robots.txt, emitted at build time. Compatible with output:"export". */
export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // Internal tooling, 301-redirected at the edge in public/_redirects
        // (2026-09-21). Listed here too so a crawler that reaches one of
        // these paths before the redirect never indexes it.
        disallow: ["/command-center/", "/admin/", "/pipeline/", "/ig/"],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
