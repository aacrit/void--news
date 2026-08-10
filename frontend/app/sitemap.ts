import type { MetadataRoute } from "next";
import { SITE_URL } from "./lib/siteMeta";

/* Static sitemap, emitted at build time as /sitemap.xml. Compatible with
   output:"export" (runs once at build, no request-time work). */
export const dynamic = "force-static";

/** Currently-prerendered public routes. Extension point: append the Deep Dive
 *  story routes here in Phase 2 (one entry per cluster id). */
const ROUTES: { path: string; changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"]; priority: number }[] = [
  { path: "/", changeFrequency: "daily", priority: 1.0 },
  { path: "/sources/", changeFrequency: "weekly", priority: 0.8 },
  { path: "/about/", changeFrequency: "monthly", priority: 0.7 },
  { path: "/onair/", changeFrequency: "daily", priority: 0.7 },
  { path: "/paper/", changeFrequency: "daily", priority: 0.6 },
  { path: "/games/", changeFrequency: "weekly", priority: 0.5 },
  { path: "/ship/", changeFrequency: "monthly", priority: 0.4 },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  return ROUTES.map((r) => ({
    url: `${SITE_URL}${r.path}`,
    lastModified,
    changeFrequency: r.changeFrequency,
    priority: r.priority,
  }));
}
