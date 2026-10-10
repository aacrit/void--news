import type { Metadata } from "next";
import PaperContent from "./PaperContent";
import { fetchInitialFeed } from "../lib/serverFeed";
import { getInitialBrief } from "../lib/serverBrief";
import { getArchiveRows } from "../lib/archive";
import { pageMetadata } from "../lib/siteMeta";
import { FEED_DISPLAYED } from "../lib/feedConfig";

/* ---------------------------------------------------------------------------
   Paper: PRERENDERED at build time (static export), like the front page.

   Async server component. It reads the SAME build-data/feed.json the home page
   reads, applies the SAME three-source floor HomeContent applies, and slices to
   FEED_DISPLAYED, so /paper and / carry the same stories in the same order.
   verify_sections.py P-02 asserts that against the served HTML.

   Determinism: the edition date is the build-time UTC string serverFeed bakes.
   Paper never calls new Date() for a rendered value.
   --------------------------------------------------------------------------- */

export const metadata: Metadata = pageMetadata({
  title: "Paper | Void News",
  description:
    "Today's twenty stories, in the order the front page prints them, laid out to print.",
  path: "/paper/",
});

export default async function PaperPage() {
  const [feed, brief, archiveRows] = await Promise.all([
    fetchInitialFeed(),
    getInitialBrief(),
    getArchiveRows(),
  ]);

  // The same gate HomeContent applies before it slices (HomeContent.tsx: a
  // story under three sources is not shown). Matching it here is what keeps the
  // two pages carrying the same twenty rather than two overlapping twenties.
  const stories = feed.stories
    .filter((s) => (s.sigilData?.sourceCount ?? s.source?.count ?? 0) >= 3)
    .slice(0, FEED_DISPLAYED);

  // A real edition count or none at all: the number of distinct days the
  // permanent archive has printed. The old masthead counted days since an
  // invented epoch of 2026-03-01, which was a published number that meant
  // nothing. An empty archive prints no number.
  const printedDays = new Set(
    archiveRows.map((r) => r.printed_on).filter(Boolean),
  );
  const editionNumber = printedDays.size > 0 ? printedDays.size: null;

  return (
    <PaperContent
      stories={stories}
      builtAt={feed.builtAt}
      editionDateline={feed.editionDateline}
      tldr={brief?.tldr_text ?? null}
      editionNumber={editionNumber}
    />
  );
}
