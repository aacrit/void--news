/* Per-issue metadata, shared by /weekly and /weekly/[week].
   Server-only: imported by the two page modules' generateMetadata. */

import type { Metadata } from "next";
import { SITE_URL, pageMetadata, sectionTitle } from "../lib/siteMeta";
import type { WeeklyDigestData } from "./types";
import { clip, essayParagraphs, formatWeekRange, issueLabel } from "./format";

/**
 * Build the share card for one issue.
 *
 * /weekly used to carry the site-wide metadata only, so every issue ever
 * published shared one title, one description and one OG card. An issue is a
 * distinct publication with its own cover story; it deserves its own.
 *
 * The cover art is the OG image when the issue has one. It is always from a
 * freely licensed source (Wikimedia Commons, or Unsplash/Pexels when a key is
 * configured) — a publisher's og:image is never used, because it is usually a
 * wire photograph and grants nothing to whoever scrapes it.
 */
export function issueMetadata(issue: WeeklyDigestData, path: string): Metadata {
  const name = issueLabel(issue.issue_number);
  const range = formatWeekRange(issue.week_start, issue.week_end);
  const headline = issue.cover_headline || issue.cover_text?.[0]?.headline || "";
  const lede = essayParagraphs(issue.cover_text?.[0]?.text || "")[0] || "";

  const title = headline
    ? sectionTitle(`${name}: ${headline}`, "Weekly")
    : sectionTitle(name, "Weekly");
  const description = lede
    ? clip(lede, 160)
    : `Weekly, ${name}, covering ${range}. The Sunday magazine from Void News.`;

  const base = pageMetadata({ title, description, path });

  /* IMAGES ARE DELIBERATELY DELETED HERE so the `opengraph-image.tsx` file
     convention can supply them. Next uses the file only when the route does
     not declare `openGraph.images` itself, and `pageMetadata` declares the
     site-wide card for every route — which is exactly why an issue's card was
     the site card before rev 71 and the raw cover photograph after it.

     The composed card (see ogCard.tsx) beats both. It is a real PNG emitted at
     build, it names the issue, and it needs no second cross-origin fetch: the
     cover photo is a hotlinked Wikimedia URL that a scraper may 404 or
     rate-limit, and when it does the share falls back to nothing. */
  const og = { ...base.openGraph } as Record<string, unknown>;
  delete og.images;
  const tw = { ...base.twitter } as Record<string, unknown>;
  delete tw.images;

  return { ...base, openGraph: og, twitter: tw } as Metadata;
}

export { SITE_URL };
