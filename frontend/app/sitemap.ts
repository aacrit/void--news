import type { MetadataRoute } from "next";
import { SITE_URL } from "./lib/siteMeta";
import { getArchiveRows, storyHref } from "./lib/archive";
import { getHistorySlugs } from "./lib/historyCatalog";
import { getWeeklyIssues } from "./lib/weeklyIssues";
import { ERAS, REGIONS } from "./history/types";

/* Static sitemap, emitted at build time as /sitemap.xml. Compatible with
   output:"export" (runs once at build, no request-time work). */
export const dynamic = "force-static";

/** Live static public routes. */
const ROUTES: { path: string; changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"]; priority: number }[] = [
  { path: "/", changeFrequency: "daily", priority: 1.0 },
  { path: "/sources/", changeFrequency: "weekly", priority: 0.8 },
  { path: "/about/", changeFrequency: "monthly", priority: 0.7 },
  { path: "/onair/", changeFrequency: "daily", priority: 0.7 },
  { path: "/history/", changeFrequency: "monthly", priority: 0.8 },
  { path: "/weekly/", changeFrequency: "weekly", priority: 0.7 },
  // The issue index. /weekly is the CURRENT issue; this is the back catalogue,
  // and it is the stable URL to link when you mean "the magazine" rather than
  // "this week".
  { path: "/weekly/archive/", changeFrequency: "weekly", priority: 0.5 },
  // The three podcast feed addresses, for people rather than apps.
  { path: "/listen/", changeFrequency: "monthly", priority: 0.5 },
  // Paper: the same twenty as the front page, laid out to print. Back 2026-09-21.
  { path: "/paper/", changeFrequency: "daily", priority: 0.6 },
  // /games is 301-redirected to home in public/_redirects (hidden for launch),
  // so it is deliberately NOT listed here: a sitemap must not advertise a
  // redirecting URL. Restore it when that section goes live.
  { path: "/ship/", changeFrequency: "monthly", priority: 0.4 },
  // The press room and the privacy page: the two pages a journalist or a
  // cautious reader looks for by name.
  { path: "/press/", changeFrequency: "monthly", priority: 0.4 },
  { path: "/privacy/", changeFrequency: "yearly", priority: 0.2 },
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
        url: `${SITE_URL}${storyHref(r.id)}`,
        lastModified: new Date(`${r.printed_on}T00:00:00Z`),
        changeFrequency: (isLatest ? "daily" : "monthly") as MetadataRoute.Sitemap[number]["changeFrequency"],
        priority: isLatest ? 0.6 : 0.3,
      };
    });
  } catch {
    // An unavailable archive just omits story URLs; the static routes still ship.
    storyEntries = [];
  }

  // Every History event: /history/<slug>/. Curated, permanent, and the most
  // link-worthy pages on the site, so they are listed individually rather than
  // left to be discovered through the landing page alone.
  const historyEntries: MetadataRoute.Sitemap = getHistorySlugs().map((slug) => ({
    url: `${SITE_URL}/history/${slug}/`,
    lastModified,
    changeFrequency: "yearly" as MetadataRoute.Sitemap[number]["changeFrequency"],
    priority: 0.5,
  }));

  // Every back issue: /weekly/<week_start>/. A published issue is permanent
  // and does not change after its Monday, so the newest decays weekly and the
  // rest monthly — the same shape the story archive uses.
  const issues = getWeeklyIssues();
  const weeklyEntries: MetadataRoute.Sitemap = issues.map((issue, i) => ({
    url: `${SITE_URL}/weekly/${issue.week_start}/`,
    lastModified: issue.created_at ? new Date(issue.created_at) : undefined,
    changeFrequency: i === 0 ? ("weekly" as const) : ("monthly" as const),
    priority: i === 0 ? 0.7 : 0.4,
  }));

  // The History browse routes: one per era, one per region (the "global"
  // region is not generated), and the threads index. Derived from the same
  // lists generateStaticParams reads, so the sitemap cannot drift from the
  // routes that exist.
  const browseEntries: MetadataRoute.Sitemap = [
    "/history/threads/",
    ...ERAS.map((e) => `/history/era/${e.id}/`),
    ...REGIONS.filter((r) => r.id !== "global").map((r) => `/history/region/${r.id}/`),
  ].map((path) => ({
    url: `${SITE_URL}${path}`,
    lastModified,
    changeFrequency: "monthly" as MetadataRoute.Sitemap[number]["changeFrequency"],
    priority: 0.4,
  }));

  return [...staticEntries, ...weeklyEntries, ...historyEntries, ...browseEntries, ...storyEntries];
}
