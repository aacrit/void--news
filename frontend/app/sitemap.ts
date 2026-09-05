import type { MetadataRoute } from "next";
import { SITE_URL } from "./lib/siteMeta";
import { getArchiveRows } from "./lib/archive";

/* Static sitemap, emitted at build time as /sitemap.xml. Compatible with
   output:"export" (runs once at build, no request-time work). */
export const dynamic = "force-static";

/** Live static public routes. */
const ROUTES: { path: string; changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"]; priority: number }[] = [
  { path: "/", changeFrequency: "daily", priority: 1.0 },
  { path: "/sources/", changeFrequency: "weekly", priority: 0.8 },
  { path: "/about/", changeFrequency: "monthly", priority: 0.7 },
  { path: "/onair/", changeFrequency: "daily", priority: 0.7 },
  // /paper and /games are 301-redirected to home in public/_redirects (hidden
  // for launch), so they are deliberately NOT listed here: a sitemap must not
  // advertise redirecting URLs. Restore them when those sections go live.
  { path: "/ship/", changeFrequency: "monthly", priority: 0.4 },
];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const lastModified = new Date();
  const staticEntries: MetadataRoute.Sitemap = ROUTES.map((r) => ({
    url: `${SITE_URL}${r.path}`,
    lastModified,
    changeFrequency: r.changeFrequency,
    priority: r.priority,
  }));

  // Every archived Deep Dive: /story/<id>/. Reads the SAME module-level archive
  // cache the /story route uses (no extra query). The latest edition changes
  // daily and is the most valuable to recrawl; older printings are effectively
  // permanent, so decay their change frequency + priority.
  let storyEntries: MetadataRoute.Sitemap = [];
  try {
    const rows = await getArchiveRows(); // ordered printed_on DESC
    const latest = rows.length > 0 ? rows[0].printed_on : null;
    storyEntries = rows.map((r) => {
      const isLatest = r.printed_on === latest;
      return {
        url: `${SITE_URL}/story/${r.id}/`,
        lastModified: new Date(`${r.printed_on}T00:00:00Z`),
        changeFrequency: (isLatest ? "daily" : "monthly") as MetadataRoute.Sitemap[number]["changeFrequency"],
        priority: isLatest ? 0.6 : 0.3,
      };
    });
  } catch {
    // An unavailable archive just omits story URLs; the static routes still ship.
    storyEntries = [];
  }

  return [...staticEntries, ...storyEntries];
}
