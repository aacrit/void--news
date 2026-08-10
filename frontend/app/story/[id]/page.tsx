import type { Metadata } from "next";
import { notFound } from "next/navigation";
import {
  getArchiveRows,
  getArchiveRowById,
  archiveRowToStory,
  archiveMembersToSpectrumSources,
  archiveMembersToStorySources,
  rowHasBiasData,
} from "../../lib/archive";
import { SITE_URL } from "../../lib/siteMeta";
import StandaloneDeepDive from "../../components/StandaloneDeepDive";

/* ---------------------------------------------------------------------------
   /story/[id] — the shareable, prerendered standalone Deep Dive.

   PRERENDERED at build time from the permanent printed archive (printed_stories,
   migration 075). generateStaticParams enumerates the WHOLE archive; the page,
   metadata, and sitemap all read the SINGLE module-level archive cache in
   lib/archive.ts, so building the entire archive is never an N+1 Supabase call.

   Static-export safe: async server component, no SSR/ISR/middleware/route
   handler. Every timestamp is preformatted at build (no Date.now/new Date in
   render) so the client's first paint is byte-identical (no React #418). NO
   client-side data fetch — the archive row carries everything.
   --------------------------------------------------------------------------- */

// Only build the ids we enumerate; any other /story/* path 404s (correct for a
// static export of a permanent archive). `force-static` keeps the segment fully
// static so an empty archive (generateStaticParams -> []) exports zero /story
// pages WITHOUT failing the build, instead of Next treating the dynamic segment
// as missing params under output: export.
export const dynamic = "force-static";
export const dynamicParams = false;

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** UTC dateline, deterministic: "Aug 8, 2026". */
function formatDatelineUTC(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()}`;
}

/** Trim to a metadata-safe length on a word boundary. */
function clip(text: string, max: number): string {
  const t = (text || "").replace(/\s+/g, " ").trim();
  if (t.length <= max) return t;
  const cut = t.slice(0, max);
  const lastSpace = cut.lastIndexOf(" ");
  return `${(lastSpace > max * 0.6 ? cut.slice(0, lastSpace) : cut).trim()}...`;
}

/** ISO datetime for datePublished — prefer first_published, else midnight UTC
 *  of the printed date. */
function publishedIso(row: { first_published: string | null; printed_on: string }): string {
  return row.first_published || `${row.printed_on}T00:00:00Z`;
}

// Sentinel id used ONLY when the archive is empty. Next 16 + output: export
// rejects a dynamic route whose generateStaticParams returns [] ("missing
// generateStaticParams"), which would fail the build on an empty archive — the
// task requires the opposite. So we emit exactly one placeholder param that the
// page renders as a 404 (notFound); it is never linked or listed in the
// sitemap, and it disappears the moment the archive has real rows.
const EMPTY_SENTINEL = "__no_archive__";

/* ── Prerender every archived story. Empty archive -> a single 404 sentinel so
      the build never fails on an empty archive (distinct from the front page's
      fail-loud on an empty feed). ──────────────────────────────────────────── */
export async function generateStaticParams(): Promise<{ id: string }[]> {
  const rows = await getArchiveRows();
  if (rows.length === 0) return [{ id: EMPTY_SENTINEL }];
  return rows.map((r) => ({ id: r.id }));
}

export async function generateMetadata(
  { params }: { params: Promise<{ id: string }> },
): Promise<Metadata> {
  const { id } = await params;
  const row = await getArchiveRowById(id);
  if (!row) {
    return { title: "Story | Void News" };
  }
  const title = `${row.title} | Void News`;
  const description = clip(
    row.summary || `Cross-source bias analysis of "${row.title}" across ${row.source_count} outlets.`,
    160,
  );
  const url = `${SITE_URL}/story/${row.id}/`;
  return {
    title,
    description,
    // Per-story OG images are a documented follow-up: og:image currently
    // inherits the site default from the root layout. When per-story cards are
    // generated, set openGraph.images / twitter.images here.
    alternates: { canonical: url },
    openGraph: {
      title,
      description,
      url,
      type: "article",
      siteName: "Void News",
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
  };
}

export default async function StoryPage(
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const row = await getArchiveRowById(id);
  if (!row) notFound();

  const story = archiveRowToStory(row);
  const spectrumSources = archiveMembersToSpectrumSources(row.members);
  const columnSources = archiveMembersToStorySources(row.members);
  const hasBiasData = rowHasBiasData(row);

  const iso = publishedIso(row);
  const datelineLabel = formatDatelineUTC(iso);
  const url = `${SITE_URL}/story/${row.id}/`;

  // schema.org NewsArticle. datePublished from first_published (ISO). Publisher
  // + author are the Void News organization. og:image intentionally omitted
  // (per-story cards are a follow-up); crawlers still get headline + summary.
  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: row.title,
    description: clip(
      row.summary || `Cross-source bias analysis of "${row.title}".`,
      200,
    ),
    datePublished: iso,
    dateModified: iso,
    url,
    mainEntityOfPage: { "@type": "WebPage", "@id": url },
    author: { "@type": "Organization", name: "Void News", url: SITE_URL },
    publisher: { "@type": "Organization", name: "Void News", url: SITE_URL },
    ...(row.category ? { articleSection: row.category } : {}),
  };

  return (
    <>
      <script
        type="application/ld+json"
        // Static JSON serialized at build time. `<` is escaped so a story title
        // containing markup can never prematurely close the </script>.
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c"),
        }}
      />
      <StandaloneDeepDive
        story={story}
        spectrumSources={spectrumSources}
        columnSources={columnSources}
        hasBiasData={hasBiasData}
        builtAt={iso}
        datelineLabel={datelineLabel}
        shareUrl={url}
      />
    </>
  );
}
